"""Testes unitários para src/api/server.py e handlers.

Valida:
- Criação da FastAPI app em modo headless
- Rota /health responde OK
- Rota /metrics responde lista
- Rotas dos handlers estão registradas
- GetTools retorna lista (sem erros de importação)
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def headless_app():
    """App FastAPI em modo headless (sem static files).

    Auth é desabilitada via env var para que os testes unitários não
    dependam de um banco de dados de usuários real.
    """
    os.environ["VECTORA_AUTH_REQUIRED"] = "false"
    from src.api.server import create_app

    return create_app()


@pytest.fixture(scope="module")
def client(headless_app):
    return TestClient(headless_app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------


class TestHealth:
    def test_health_ok(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert "version" in body

    def test_health_version_non_empty(self, client):
        response = client.get("/health")
        assert response.json()["version"] != ""


# ---------------------------------------------------------------------------
# /metrics
# ---------------------------------------------------------------------------


class TestMetrics:
    def test_metrics_returns_list(self, client):
        response = client.get("/metrics")
        assert response.status_code == 200
        assert isinstance(response.json(), list)


# ---------------------------------------------------------------------------
# Rotas registradas
# ---------------------------------------------------------------------------


class TestRoutes:
    def _route_paths(self, app) -> list[str]:
        return [r.path for r in app.routes]

    def test_stream_chat_route_exists(self, headless_app):
        paths = self._route_paths(headless_app)
        assert "/vectora.chat.v1.ChatService/StreamChat" in paths

    def test_resume_chat_route_exists(self, headless_app):
        paths = self._route_paths(headless_app)
        assert "/vectora.chat.v1.ChatService/ResumeChat" in paths

    def test_get_tools_route_exists(self, headless_app):
        paths = self._route_paths(headless_app)
        assert "/vectora.chat.v1.ChatService/GetTools" in paths

    def test_thread_routes_exist(self, headless_app):
        paths = self._route_paths(headless_app)
        for route in (
            "/vectora.chat.v1.ThreadService/CreateThread",
            "/vectora.chat.v1.ThreadService/GetThread",
            "/vectora.chat.v1.ThreadService/ListThreads",
            "/vectora.chat.v1.ThreadService/DeleteThread",
            "/vectora.chat.v1.ThreadService/GetHistory",
        ):
            assert route in paths, f"Rota ausente: {route}"


# ---------------------------------------------------------------------------
# GetTools (endpoint síncrono — pode testar sem graph)
# ---------------------------------------------------------------------------


class TestGetTools:
    def test_get_tools_returns_200(self, client):
        response = client.get("/vectora.chat.v1.ChatService/GetTools")
        assert response.status_code == 200

    def test_get_tools_has_tools_key(self, client):
        response = client.get("/vectora.chat.v1.ChatService/GetTools")
        body = response.json()
        assert "tools" in body
        assert isinstance(body["tools"], list)

    def test_get_tools_each_has_name(self, client):
        response = client.get("/vectora.chat.v1.ChatService/GetTools")
        tools = response.json()["tools"]
        if tools:  # pode ser vazia em ambiente de teste sem ALL_TOOLS
            for t in tools:
                assert "name" in t
                assert "render_hint" in t


# ---------------------------------------------------------------------------
# Modo chat sem static dir não levanta exceção
# ---------------------------------------------------------------------------


class TestChatModeWithoutStaticDir:
    def test_chat_mode_with_frontend_proxy(self):
        """create_app(serve_static=True) registra o proxy do frontend sem explodir."""
        from src.api.server import create_app

        app = create_app(serve_static=True)
        c = TestClient(app, raise_server_exceptions=False)
        resp = c.get("/health")
        assert resp.status_code == 200

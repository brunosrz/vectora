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
    from backend.api.server import create_app

    return create_app()


@pytest.fixture(scope="module")
def client(headless_app):
    return TestClient(headless_app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------


class TestLifespan:
    """Regressão: o ciclo de vida do app precisa INICIAR o embedding worker.

    O bug original: ``_lifespan`` parava o BackgroundEmbeddingWorker no shutdown
    mas nunca o iniciava no startup, então os chunks enfileirados por
    ``ingest_docs``/``ingest_directory`` ficavam "pending" para sempre e o RAG
    nunca recuperava nada — sem nenhum teste pegando isso (os testes de RAG
    mockavam LanceDB/Cohere e davam falso verde).
    """

    def test_lifespan_starts_embedding_worker(self, headless_app, monkeypatch):
        import backend.services.background as bg

        started = {"value": False}

        class _FakeWorker:
            async def start(self) -> None:
                started["value"] = True

            async def stop(self, *_a, **_k) -> None:
                pass

        async def _fake_get_worker() -> _FakeWorker:
            return _FakeWorker()

        monkeypatch.setattr(bg, "get_background_worker", _fake_get_worker)

        # Entrar/sair do TestClient como context manager dispara o lifespan.
        with TestClient(headless_app, raise_server_exceptions=False):
            pass

        assert started["value"], (
            "_lifespan não iniciou o BackgroundEmbeddingWorker — chunks "
            "enfileirados ficariam pending e o RAG não recuperaria nada."
        )


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


def _collect_route_paths(routes) -> list[str]:
    """Coleta paths recursivamente — FastAPI 0.138 usa _IncludedRouter sem .path."""
    paths: list[str] = []
    for r in routes:
        if hasattr(r, "path") and r.path is not None:
            paths.append(r.path)
        orig = getattr(r, "original_router", None)
        if orig is not None and hasattr(orig, "routes"):
            paths.extend(_collect_route_paths(orig.routes))
        elif hasattr(r, "routes") and r.routes:
            paths.extend(_collect_route_paths(r.routes))
    return paths


class TestRoutes:
    def _route_paths(self, app) -> list[str]:
        return _collect_route_paths(app.routes)

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

    def test_share_routes_exist(self, headless_app):
        paths = self._route_paths(headless_app)
        assert "/threads/share" in paths
        assert "/threads/share/{token}" in paths


# ---------------------------------------------------------------------------
# MCP sempre-ativo (Sprint 2) — montado em /mcp + lifespan composto
# ---------------------------------------------------------------------------


class TestMcpMount:
    """O MCP sobe com todo boot do backend, montado em /mcp, e o ``_lifespan``
    do FastAPI compõe o bootstrap de env do MCP — o Starlette NÃO roda o
    lifespan de um sub-app montado, então sem isso o lifespan do MCP nunca
    executa no `vectora start`."""

    def test_mcp_mounted_at_slash_mcp(self, headless_app):
        paths = _collect_route_paths(headless_app.routes)
        assert "/mcp" in paths, "MCP não montado em /mcp"

    def test_api_tools_schema_route_exists(self, headless_app):
        paths = _collect_route_paths(headless_app.routes)
        assert "/api/tools/schema" in paths

    def test_lifespan_runs_mcp_env_bootstrap(self, headless_app, monkeypatch):
        import backend.mcp.env_bootstrap as eb

        called = {"value": False}

        def _fake_bootstrap() -> bool:
            called["value"] = True
            return False

        monkeypatch.setattr(eb, "bootstrap_env_from_mcp", _fake_bootstrap)

        with TestClient(headless_app, raise_server_exceptions=False):
            pass

        assert called["value"], (
            "_lifespan não compôs o bootstrap de env do MCP — o lifespan do "
            "MCP montado em /mcp nunca roda no boot do backend."
        )


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
        from backend.api.server import create_app

        app = create_app(serve_static=True)
        c = TestClient(app, raise_server_exceptions=False)
        resp = c.get("/health")
        assert resp.status_code == 200

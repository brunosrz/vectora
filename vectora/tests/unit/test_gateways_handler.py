"""Testes para backend/api/handlers/gateways.py (gateways Ollama e OpenRouter).

Valida:
- GET /gateways/ollama/models: host inacessível -> reachable=False (nunca
  500); host acessível -> lista de modelos.
- POST/GET/DELETE /gateways/ollama/registered: CRUD de modelos registrados.
- POST/DELETE /gateways/openrouter/key: valida contra /auth/key antes de
  persistir; nunca salva key rejeitada.
- GET /gateways/openrouter/models: catálogo cacheado, filtro por `q`, erro de
  rede não vira 500.
- POST/GET/DELETE /gateways/openrouter/registered: mesmo CRUD do Ollama.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def app():
    os.environ["VECTORA_AUTH_REQUIRED"] = "false"
    from backend.api.server import create_app

    return create_app(serve_static=False)


@pytest.fixture(scope="module")
def client(app):
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def clean_openrouter_key():
    """Garante que OPENROUTER_API_KEY não vaza de um teste para o outro —
    os testes de /gateways/openrouter/key escrevem em os.environ de verdade."""
    yield
    os.environ.pop("OPENROUTER_API_KEY", None)
    from backend.settings import settings

    object.__setattr__(settings, "openrouter_api_key", None)


class TestOllamaDiscovery:
    def test_host_unreachable_returns_reachable_false_not_500(self, client):
        resp = client.get("/gateways/ollama/models")
        assert resp.status_code == 200
        body = resp.json()
        assert body["reachable"] is False
        assert body["models"] == []

    def test_host_reachable_returns_models(self, client):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "models": [
                {"name": "qwen3:8b", "size": 123, "modified_at": "2026-01-01"},
                {"name": "llama3.1:8b", "size": 456},
            ]
        }
        with patch("httpx.AsyncClient") as mock_httpx:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_ctx.get = AsyncMock(return_value=mock_response)
            mock_httpx.return_value = mock_ctx

            resp = client.get("/gateways/ollama/models")

        assert resp.status_code == 200
        body = resp.json()
        assert body["reachable"] is True
        assert [m["name"] for m in body["models"]] == ["qwen3:8b", "llama3.1:8b"]


class TestOllamaRegisteredModels:
    def test_register_list_and_delete(self, client):
        create = client.post("/gateways/ollama/registered", json={"tag": "qwen3:8b"})
        assert create.status_code == 200
        model_id = create.json()["id"]
        assert create.json()["tag"] == "qwen3:8b"

        listing = client.get("/gateways/ollama/registered")
        assert listing.status_code == 200
        assert any(m["id"] == model_id for m in listing.json())

        deleted = client.delete(f"/gateways/ollama/registered/{model_id}")
        assert deleted.status_code == 200
        listing_after = client.get("/gateways/ollama/registered")
        assert all(m["id"] != model_id for m in listing_after.json())

    def test_register_empty_tag_returns_400(self, client):
        resp = client.post("/gateways/ollama/registered", json={"tag": "   "})
        assert resp.status_code == 400

    def test_register_duplicate_tag_returns_409(self, client):
        client.post("/gateways/ollama/registered", json={"tag": "dup-model"})
        resp = client.post("/gateways/ollama/registered", json={"tag": "dup-model"})
        assert resp.status_code == 409


class TestOpenRouterKey:
    def test_status_not_configured_by_default(self, client, clean_openrouter_key):
        os.environ.pop("OPENROUTER_API_KEY", None)
        resp = client.get("/gateways/openrouter/status")
        assert resp.status_code == 200
        assert resp.json() == {"configured": False, "masked": ""}

    def test_set_key_valid_persists_and_masks(
        self, client, clean_openrouter_key, tmp_path
    ):
        mock_response = MagicMock()
        mock_response.status_code = 200

        with (
            patch("httpx.AsyncClient") as mock_httpx,
            patch(
                "backend.api.handlers.gateways._env_file",
                return_value=tmp_path / ".env",
            ),
        ):
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_ctx.get = AsyncMock(return_value=mock_response)
            mock_httpx.return_value = mock_ctx

            resp = client.post(
                "/gateways/openrouter/key", json={"api_key": "sk-or-v1-abcdef123456"}
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["configured"] is True
        assert body["masked"].startswith("sk-or-")
        assert "abcdef123456" not in body["masked"]
        assert os.environ["OPENROUTER_API_KEY"] == "sk-or-v1-abcdef123456"

    def test_set_key_rejected_by_openrouter_returns_400(
        self, client, clean_openrouter_key, tmp_path
    ):
        mock_response = MagicMock()
        mock_response.status_code = 401

        with (
            patch("httpx.AsyncClient") as mock_httpx,
            patch(
                "backend.api.handlers.gateways._env_file",
                return_value=tmp_path / ".env",
            ),
        ):
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_ctx.get = AsyncMock(return_value=mock_response)
            mock_httpx.return_value = mock_ctx

            resp = client.post("/gateways/openrouter/key", json={"api_key": "bad-key"})

        assert resp.status_code == 400
        assert "OPENROUTER_API_KEY" not in os.environ

    def test_set_key_empty_returns_400_without_network_call(
        self, client, clean_openrouter_key
    ):
        with patch("httpx.AsyncClient") as mock_httpx:
            resp = client.post("/gateways/openrouter/key", json={"api_key": "   "})
        assert resp.status_code == 400
        mock_httpx.assert_not_called()

    def test_clear_key_removes_env(self, client, clean_openrouter_key, tmp_path):
        os.environ["OPENROUTER_API_KEY"] = "sk-or-v1-should-be-removed"
        with patch(
            "backend.api.handlers.gateways._env_file",
            return_value=tmp_path / ".env",
        ):
            resp = client.delete("/gateways/openrouter/key")
        assert resp.status_code == 200
        assert resp.json() == {"configured": False, "masked": ""}
        assert "OPENROUTER_API_KEY" not in os.environ


class TestOpenRouterCatalog:
    @staticmethod
    def _reset_cache() -> None:
        from backend.api.handlers.gateways import _catalog_cache

        _catalog_cache["fetched_at"] = float("-inf")
        _catalog_cache["models"] = []

    @pytest.fixture(autouse=True)
    def _isolated_cache(self):
        # Reseta antes E depois — o fixture `client` deste arquivo é
        # module-scoped (mesmo TestClient/app pra todos os testes), então
        # qualquer estado deixado em `_catalog_cache` por este teste não
        # pode vazar pro próximo, seja qual for a ordem de execução.
        self._reset_cache()
        yield
        self._reset_cache()

    @contextmanager
    def _mocked_http_client(
        self, app, handler: Callable[[httpx.Request], httpx.Response]
    ) -> Iterator[None]:
        """Troca o client HTTP do endpoint via dependency override do
        FastAPI — mais correto/idiomático que `unittest.mock.patch
        ("httpx.AsyncClient", ...)`, resolvido pelo próprio FastAPI dentro
        do mesmo contexto async da request em vez de mutar um atributo
        global. (O flake real do catálogo em CI era outro — ver
        `test_catalog_stale_sentinel_survives_low_monotonic_clock` — mas
        dependency override continua a forma certa de mockar isso.)
        """
        from backend.api.handlers.gateways import _get_http_client

        async def _fake_client():
            async with httpx.AsyncClient(
                transport=httpx.MockTransport(handler)
            ) as client:
                yield client

        app.dependency_overrides[_get_http_client] = _fake_client
        try:
            yield
        finally:
            app.dependency_overrides.pop(_get_http_client, None)

    def test_catalog_returns_models(self, app, client):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "data": [
                        {
                            "id": "openai/gpt-4o",
                            "name": "GPT-4o",
                            "context_length": 128000,
                        },
                        {
                            "id": "anthropic/claude-3.5-sonnet",
                            "name": "Claude 3.5 Sonnet",
                        },
                    ]
                },
            )

        with self._mocked_http_client(app, handler):
            resp = client.get("/gateways/openrouter/models")

        assert resp.status_code == 200
        ids = [m["id"] for m in resp.json()["models"]]
        assert ids == ["openai/gpt-4o", "anthropic/claude-3.5-sonnet"]

    def test_catalog_filters_by_q(self, app, client):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "data": [
                        {"id": "openai/gpt-4o", "name": "GPT-4o"},
                        {
                            "id": "anthropic/claude-3.5-sonnet",
                            "name": "Claude 3.5 Sonnet",
                        },
                    ]
                },
            )

        with self._mocked_http_client(app, handler):
            resp = client.get("/gateways/openrouter/models", params={"q": "claude"})

        assert resp.status_code == 200
        ids = [m["id"] for m in resp.json()["models"]]
        assert ids == ["anthropic/claude-3.5-sonnet"]

    def test_catalog_network_error_returns_empty_not_500(self, app, client):
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("network down")

        with self._mocked_http_client(app, handler):
            resp = client.get("/gateways/openrouter/models")
        assert resp.status_code == 200
        assert resp.json() == {"models": []}

    def test_catalog_stale_sentinel_survives_low_monotonic_clock(
        self, app, client, monkeypatch
    ):
        """Bug real reproduzido só em CI (Linux, VM efêmera recém-bootada),
        nunca localmente: `time.monotonic()` não conta a partir de zero —
        reflete o uptime da máquina. Numa VM com menos de
        `_OPENROUTER_CATALOG_TTL_S` (3600s) de uptime, `now` já é menor que
        o TTL sozinho; um sentinela `fetched_at=0.0` faz `now - 0.0 > TTL`
        dar falso, então o cache "resetado" parece recém-buscado e o
        endpoint devolve a lista vazia direto, sem nunca tentar buscar —
        exatamente o `assert [] == [...]` visto na CI. Simula esse uptime
        baixo aqui: se o sentinela correto (`-inf`) estiver em uso, o fetch
        acontece de qualquer forma."""
        import time as time_mod

        monkeypatch.setattr(time_mod, "monotonic", lambda: 45.0)

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200, json={"data": [{"id": "openai/gpt-4o", "name": "GPT-4o"}]}
            )

        with self._mocked_http_client(app, handler):
            resp = client.get("/gateways/openrouter/models")

        assert resp.status_code == 200
        ids = [m["id"] for m in resp.json()["models"]]
        assert ids == ["openai/gpt-4o"]


class TestOpenRouterRegisteredModels:
    def test_register_list_and_delete(self, client):
        create = client.post(
            "/gateways/openrouter/registered", json={"tag": "openai/gpt-4o"}
        )
        assert create.status_code == 200
        model_id = create.json()["id"]
        assert create.json()["tag"] == "openai/gpt-4o"

        listing = client.get("/gateways/openrouter/registered")
        assert listing.status_code == 200
        assert any(m["id"] == model_id for m in listing.json())

        deleted = client.delete(f"/gateways/openrouter/registered/{model_id}")
        assert deleted.status_code == 200
        listing_after = client.get("/gateways/openrouter/registered")
        assert all(m["id"] != model_id for m in listing_after.json())

    def test_register_empty_tag_returns_400(self, client):
        resp = client.post("/gateways/openrouter/registered", json={"tag": "   "})
        assert resp.status_code == 400

    def test_register_duplicate_tag_returns_409(self, client):
        client.post("/gateways/openrouter/registered", json={"tag": "dup/model"})
        resp = client.post("/gateways/openrouter/registered", json={"tag": "dup/model"})
        assert resp.status_code == 409

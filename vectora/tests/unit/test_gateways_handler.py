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

import functools
import os
from collections.abc import Callable
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    os.environ["VECTORA_AUTH_REQUIRED"] = "false"
    from backend.api.server import create_app

    app = create_app(serve_static=False)
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

        _catalog_cache["fetched_at"] = 0.0
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

    @staticmethod
    def _mock_async_client(
        handler: Callable[[httpx.Request], httpx.Response],
    ) -> functools.partial[httpx.AsyncClient]:
        """`httpx.AsyncClient` real, só trocando o transporte por
        `httpx.MockTransport` — em vez de simular o protocolo de context
        manager assíncrono (`__aenter__`/`__aexit__`) na mão com MagicMock,
        que é frágil entre implementações de event loop diferentes (uvloop
        no CI Linux vs asyncio puro no Windows). Isso exercita o client HTTP
        de verdade, só a rede é falsa."""
        return functools.partial(
            httpx.AsyncClient, transport=httpx.MockTransport(handler)
        )

    def test_catalog_returns_models(self, client):
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

        with patch("httpx.AsyncClient", self._mock_async_client(handler)):
            resp = client.get("/gateways/openrouter/models")

        assert resp.status_code == 200
        ids = [m["id"] for m in resp.json()["models"]]
        assert ids == ["openai/gpt-4o", "anthropic/claude-3.5-sonnet"]

    def test_catalog_filters_by_q(self, client):
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

        with patch("httpx.AsyncClient", self._mock_async_client(handler)):
            resp = client.get("/gateways/openrouter/models", params={"q": "claude"})

        assert resp.status_code == 200
        ids = [m["id"] for m in resp.json()["models"]]
        assert ids == ["anthropic/claude-3.5-sonnet"]

    def test_catalog_network_error_returns_empty_not_500(self, client):
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("network down")

        with patch("httpx.AsyncClient", self._mock_async_client(handler)):
            resp = client.get("/gateways/openrouter/models")
        assert resp.status_code == 200
        assert resp.json() == {"models": []}


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

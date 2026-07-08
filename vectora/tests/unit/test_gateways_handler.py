"""Testes para backend/api/handlers/gateways.py (gateway Ollama).

Valida:
- GET /gateways/ollama/models: host inacessível -> reachable=False (nunca
  500); host acessível -> lista de modelos.
- POST/GET/DELETE /gateways/ollama/registered: CRUD de modelos registrados.
"""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    os.environ["VECTORA_AUTH_REQUIRED"] = "false"
    from backend.api.server import create_app

    app = create_app(serve_static=False)
    return TestClient(app, raise_server_exceptions=False)


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

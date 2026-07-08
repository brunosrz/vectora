"""Testes para backend/api/handlers/models.py.

Valida:
- GET /models/providers devolve `providers` (lista) e `dynamic_models` (vazia
  por padrão).
- Modelo Ollama registrado via /gateways/ollama/registered aparece em
  `dynamic_models` como "ollama:<tag>".
- Modelo OpenRouter registrado via /gateways/openrouter/registered aparece em
  `dynamic_models` como "openrouter:<tag>", junto (não em vez) do Ollama.
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    os.environ["VECTORA_AUTH_REQUIRED"] = "false"
    from backend.api.server import create_app

    app = create_app(serve_static=False)
    return TestClient(app, raise_server_exceptions=False)


class TestModelsProviders:
    def test_returns_providers_and_empty_dynamic_models(self, client):
        resp = client.get("/models/providers")
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body["providers"], list)
        assert isinstance(body["dynamic_models"], list)

    def test_registered_ollama_model_appears_in_dynamic_models(self, client):
        tag = "providers-test-tag"
        # DB real compartilhada entre execuções (ver threads.py::_get_db) —
        # limpa resíduo de uma execução anterior antes de registrar de novo.
        for existing in client.get("/gateways/ollama/registered").json():
            if existing["tag"] == tag:
                client.delete(f"/gateways/ollama/registered/{existing['id']}")

        create = client.post("/gateways/ollama/registered", json={"tag": tag})
        assert create.status_code == 200
        model_id = create.json()["id"]

        resp = client.get("/models/providers")
        assert resp.status_code == 200
        ids = [m["id"] for m in resp.json()["dynamic_models"]]
        assert f"ollama:{tag}" in ids

        client.delete(f"/gateways/ollama/registered/{model_id}")

    def test_registered_openrouter_model_appears_alongside_ollama(self, client):
        ollama_tag = "providers-test-ollama-tag"
        openrouter_tag = "providers-test-openrouter/model"
        for existing in client.get("/gateways/ollama/registered").json():
            if existing["tag"] == ollama_tag:
                client.delete(f"/gateways/ollama/registered/{existing['id']}")
        for existing in client.get("/gateways/openrouter/registered").json():
            if existing["tag"] == openrouter_tag:
                client.delete(f"/gateways/openrouter/registered/{existing['id']}")

        ollama_id = client.post(
            "/gateways/ollama/registered", json={"tag": ollama_tag}
        ).json()["id"]
        openrouter_id = client.post(
            "/gateways/openrouter/registered", json={"tag": openrouter_tag}
        ).json()["id"]

        resp = client.get("/models/providers")
        assert resp.status_code == 200
        ids = [m["id"] for m in resp.json()["dynamic_models"]]
        assert f"ollama:{ollama_tag}" in ids
        assert f"openrouter:{openrouter_tag}" in ids

        client.delete(f"/gateways/ollama/registered/{ollama_id}")
        client.delete(f"/gateways/openrouter/registered/{openrouter_id}")

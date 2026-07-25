"""Testes para backend/api/handlers/flags.py.

Valida:
- GET /settings/flags reflete settings.enable_features_beta por padrão.
- VECTORA_DEV=1 ativa enable_features_beta mesmo com o setting em False
  (Electron em modo dev propaga essa env var pro processo do backend).
- Só o valor exato "1" ativa — qualquer outro valor não conta como dev mode.
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("VECTORA_AUTH_REQUIRED", "false")
    from backend.api.server import create_app

    app = create_app(serve_static=False)
    return TestClient(app, raise_server_exceptions=False)


class TestGetFlags:
    def test_always_enabled_by_default(self, client, monkeypatch):
        """Features beta agora são estáveis e habilitadas por padrão."""
        monkeypatch.delenv("VECTORA_DEV", raising=False)
        resp = client.get("/settings/flags")
        assert resp.status_code == 200
        assert resp.json()["enable_features_beta"] is True

    def test_vectora_dev_does_not_affect_it(self, client, monkeypatch):
        """Independente de VECTORA_DEV, agora é sempre True."""
        for value in ("1", "0", "true", ""):
            monkeypatch.setenv("VECTORA_DEV", value)
            resp = client.get("/settings/flags")
            assert resp.json()["enable_features_beta"] is True

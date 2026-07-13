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
    def test_reflects_settings_by_default(self, client, monkeypatch):
        monkeypatch.delenv("VECTORA_DEV", raising=False)
        resp = client.get("/settings/flags")
        assert resp.status_code == 200
        assert resp.json()["enable_features_beta"] is False

    def test_vectora_dev_1_forces_beta_flags_on(self, client, monkeypatch):
        monkeypatch.setenv("VECTORA_DEV", "1")
        resp = client.get("/settings/flags")
        assert resp.status_code == 200
        assert resp.json()["enable_features_beta"] is True

    def test_vectora_dev_non_1_value_does_not_enable(self, client, monkeypatch):
        for value in ("true", "0", "yes", ""):
            monkeypatch.setenv("VECTORA_DEV", value)
            resp = client.get("/settings/flags")
            assert resp.json()["enable_features_beta"] is False, (
                f"VECTORA_DEV={value!r} não deveria ativar beta flags"
            )

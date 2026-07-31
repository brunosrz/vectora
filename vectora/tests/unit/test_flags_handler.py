"""Testes para backend/api/handlers/flags.py.

Valida:
- GET /settings/flags reflete settings.enable_features_beta por padrão.
- VECTORA_DEV=1 ativa enable_features_beta mesmo com o setting em False
  (Electron em modo dev propaga essa env var pro processo do backend).
- Só o valor exato "1" ativa — qualquer outro valor não conta como dev mode.
- local_configured distingue "auth desabilitada porque o wizard rodou" de
  "auth desabilitada por acidente" (bug real relatado: env var externa
  desligando auth sem o wizard nunca ter rodado, fabricando um usuário
  "Local User" fantasma no frontend).
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def _isolated_runtime_settings(tmp_path: Path, monkeypatch):
    """Isola local_user_name de cada teste (nunca lê/escreve o ~/.vectora real)."""
    from backend.workspace import runtime_settings as rs_module
    from backend.workspace.runtime_settings import RuntimeSettings

    fresh = RuntimeSettings(path=tmp_path / "checkpoints.db")
    monkeypatch.setattr(rs_module, "runtime_settings", fresh)
    return fresh


@pytest.fixture
def client(monkeypatch, _isolated_runtime_settings):
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


class TestLocalConfigured:
    def test_false_quando_wizard_nunca_rodou(self, client, _isolated_runtime_settings):
        """auth_required=false sem local_user_name persistido (bug real:
        VECTORA_AUTH_REQUIRED=false esquecido num .env externo) — o guard do
        frontend usa isso pra nunca pular o onboarding silenciosamente."""
        resp = client.get("/settings/flags")
        assert resp.json()["local_configured"] is False

    def test_true_apos_setup_local(self, client, _isolated_runtime_settings):
        _isolated_runtime_settings.set_local_user("Bruno", "Vectora")
        resp = client.get("/settings/flags")
        assert resp.json()["local_configured"] is True


class TestEnableKanbanMode:
    """O 3º modo de interface é dev-only: `VECTORA_DEV=1` exato.

    Mesmo mecanismo que gateou o IDE mode antes de graduar. Fora do dev, o
    usuário não vê a opção existir.
    """

    def test_habilitado_com_vectora_dev_1(self, client, monkeypatch):
        monkeypatch.setenv("VECTORA_DEV", "1")
        assert client.get("/settings/flags").json()["enable_kanban_mode"] is True

    def test_sem_a_env_fica_desligado(self, client, monkeypatch):
        monkeypatch.delenv("VECTORA_DEV", raising=False)
        assert client.get("/settings/flags").json()["enable_kanban_mode"] is False

    @pytest.mark.parametrize("valor", ["0", "true", "yes", "", " 1", "01"])
    def test_so_o_valor_1_exato_ativa(self, client, monkeypatch, valor):
        """Erro/borda: `true`/`yes` parecem ligar mas não ligam — a convenção
        do projeto é `1` exato, e aceitar variações faria a flag ligar sem
        querer em ambiente de usuário."""
        monkeypatch.setenv("VECTORA_DEV", valor)
        assert client.get("/settings/flags").json()["enable_kanban_mode"] is False

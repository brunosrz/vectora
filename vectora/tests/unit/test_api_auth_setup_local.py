"""Testes de POST /auth/setup-local.

Cobre: configura a instância pra modo local (sem conta) só no primeiro acesso.
Persiste auth_required=false e nome/empresa do usuário local em app_settings
(SQLite, via runtime_settings) — nunca no .env, que fica só pra segredos.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from backend.api.handlers.auth import SetupLocalRequest, setup_local_endpoint
from backend.workspace.runtime_settings import RuntimeSettings


@pytest.fixture(autouse=True)
def _isolated_runtime_settings(tmp_path: Path, monkeypatch):
    """Isola cada teste com um RuntimeSettings próprio (nunca toca o real)."""
    from backend.workspace import runtime_settings as rs_module

    fresh = RuntimeSettings(path=tmp_path / "checkpoints.db")
    monkeypatch.setattr(rs_module, "runtime_settings", fresh)
    yield fresh


def _async_bool(value: bool):
    async def _inner() -> bool:
        return value

    return _inner()


def test_setup_local_exige_ausencia_de_usuarios():
    with patch("backend.rbac.auth.has_users", lambda: _async_bool(True)):
        with pytest.raises(HTTPException) as exc:
            asyncio.run(setup_local_endpoint(SetupLocalRequest(name="Bruno")))
    assert exc.value.status_code == 409


def test_setup_local_nome_obrigatorio():
    with patch("backend.rbac.auth.has_users", lambda: _async_bool(False)):
        with pytest.raises(HTTPException) as exc:
            asyncio.run(setup_local_endpoint(SetupLocalRequest(name="   ")))
    assert exc.value.status_code == 422


def test_setup_local_persiste_e_desabilita_auth(_isolated_runtime_settings):
    with patch("backend.rbac.auth.has_users", lambda: _async_bool(False)):
        result = asyncio.run(
            setup_local_endpoint(SetupLocalRequest(name="Bruno", company="Vectora"))
        )

    assert result.ok is True
    assert _isolated_runtime_settings.auth_required is False
    assert _isolated_runtime_settings.local_user_name == "Bruno"
    assert _isolated_runtime_settings.local_user_company == "Vectora"


def test_setup_local_nao_toca_env_file(_isolated_runtime_settings, tmp_path: Path):
    """auth_required e nome/empresa vão só pro app_settings — nada no .env."""
    env_file = tmp_path / ".env"
    with patch("backend.rbac.auth.has_users", lambda: _async_bool(False)):
        asyncio.run(setup_local_endpoint(SetupLocalRequest(name="Bruno")))
    assert not env_file.exists()


def test_setup_local_empresa_opcional_vai_pro_store(_isolated_runtime_settings):
    with patch("backend.rbac.auth.has_users", lambda: _async_bool(False)):
        result = asyncio.run(setup_local_endpoint(SetupLocalRequest(name="Bruno")))

    assert result.ok is True
    assert _isolated_runtime_settings.local_user_name == "Bruno"
    assert _isolated_runtime_settings.local_user_company == ""

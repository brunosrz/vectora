"""Testes de POST /auth/setup-local.

Cobre: configura a instância pra modo local (sem conta) só no primeiro
acesso, persiste VECTORA_AUTH_REQUIRED=false + nome/empresa sem tocar disco
de verdade (upsert_env_key e _env_file mockados, mesmo padrão de
test_admin.py::test_patch_api_keys_calls_upsert).
"""

from __future__ import annotations

import asyncio
import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from backend.api.handlers.auth import SetupLocalRequest, setup_local_endpoint


@pytest.fixture(autouse=True)
def _cleanup_env():
    """Restaura VECTORA_AUTH_REQUIRED e as envs locais entre testes."""
    keys = (
        "VECTORA_AUTH_REQUIRED",
        "VECTORA_LOCAL_USER_NAME",
        "VECTORA_LOCAL_USER_COMPANY",
    )
    before = {k: os.environ.get(k) for k in keys}
    yield
    for k, v in before.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v


def _async_bool(value: bool):
    async def _inner() -> bool:
        return value

    return _inner()


def test_setup_local_exige_ausencia_de_usuarios():
    with patch("backend.services.auth.has_users", lambda: _async_bool(True)):
        with pytest.raises(HTTPException) as exc:
            asyncio.run(setup_local_endpoint(SetupLocalRequest(name="Bruno")))
    assert exc.value.status_code == 409


def test_setup_local_nome_obrigatorio():
    with patch("backend.services.auth.has_users", lambda: _async_bool(False)):
        with pytest.raises(HTTPException) as exc:
            asyncio.run(setup_local_endpoint(SetupLocalRequest(name="   ")))
    assert exc.value.status_code == 422


def test_setup_local_persiste_e_desabilita_auth():
    with (
        patch("backend.services.auth.has_users", lambda: _async_bool(False)),
        patch("backend.cli.keys.upsert_env_key") as mock_upsert,
        patch("backend.api.handlers.auth._env_file", return_value=MagicMock()),
    ):
        result = asyncio.run(
            setup_local_endpoint(SetupLocalRequest(name="Bruno", company="Vectora"))
        )

    assert result.ok is True
    assert os.environ["VECTORA_AUTH_REQUIRED"] == "false"
    assert os.environ["VECTORA_LOCAL_USER_NAME"] == "Bruno"
    assert os.environ["VECTORA_LOCAL_USER_COMPANY"] == "Vectora"

    written = {call.args[1]: call.args[2] for call in mock_upsert.call_args_list}
    assert written["VECTORA_AUTH_REQUIRED"] == "false"
    assert written["VECTORA_LOCAL_USER_NAME"] == "Bruno"
    assert written["VECTORA_LOCAL_USER_COMPANY"] == "Vectora"


def test_setup_local_empresa_opcional_nao_grava_chave_vazia():
    with (
        patch("backend.services.auth.has_users", lambda: _async_bool(False)),
        patch("backend.cli.keys.upsert_env_key") as mock_upsert,
        patch("backend.api.handlers.auth._env_file", return_value=MagicMock()),
    ):
        result = asyncio.run(setup_local_endpoint(SetupLocalRequest(name="Bruno")))

    assert result.ok is True
    written_keys = {call.args[1] for call in mock_upsert.call_args_list}
    assert "VECTORA_LOCAL_USER_COMPANY" not in written_keys

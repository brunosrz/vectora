"""Testes de POST /auth/setup-local.

Cobre: configura a instância pra modo local (sem conta) só no primeiro acesso.
No .env vai só VECTORA_AUTH_REQUIRED (config de runtime); nome/empresa do
usuário local são dados não-secretos e vão pro store app-owned via
write_local_user. upsert_env_key/write_local_user/_env_file mockados (não toca
disco), mesmo padrão de test_admin.py::test_patch_api_keys_calls_upsert.
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
    with patch("backend.rbac.auth.has_users", lambda: _async_bool(True)):
        with pytest.raises(HTTPException) as exc:
            asyncio.run(setup_local_endpoint(SetupLocalRequest(name="Bruno")))
    assert exc.value.status_code == 409


def test_setup_local_nome_obrigatorio():
    with patch("backend.rbac.auth.has_users", lambda: _async_bool(False)):
        with pytest.raises(HTTPException) as exc:
            asyncio.run(setup_local_endpoint(SetupLocalRequest(name="   ")))
    assert exc.value.status_code == 422


def test_setup_local_persiste_e_desabilita_auth():
    with (
        patch("backend.rbac.auth.has_users", lambda: _async_bool(False)),
        patch("backend.cli.keys.upsert_env_key") as mock_upsert,
        patch("backend.services.local_user.write_local_user") as mock_write_user,
        patch("backend.api.handlers.auth._env_file", return_value=MagicMock()),
    ):
        result = asyncio.run(
            setup_local_endpoint(SetupLocalRequest(name="Bruno", company="Vectora"))
        )

    assert result.ok is True
    assert os.environ["VECTORA_AUTH_REQUIRED"] == "false"

    # No .env vai SÓ o flag de modo — nome/empresa nunca (dado não-secreto).
    written = {call.args[1]: call.args[2] for call in mock_upsert.call_args_list}
    assert written == {"VECTORA_AUTH_REQUIRED": "false"}
    assert "VECTORA_LOCAL_USER_NAME" not in written
    assert "VECTORA_LOCAL_USER_COMPANY" not in written

    # Nome/empresa vão pro store app-owned (~/.vectora/local_user.json).
    mock_write_user.assert_called_once_with("Bruno", "Vectora")


def test_setup_local_empresa_opcional_vai_pro_store():
    with (
        patch("backend.rbac.auth.has_users", lambda: _async_bool(False)),
        patch("backend.cli.keys.upsert_env_key"),
        patch("backend.services.local_user.write_local_user") as mock_write_user,
        patch("backend.api.handlers.auth._env_file", return_value=MagicMock()),
    ):
        result = asyncio.run(setup_local_endpoint(SetupLocalRequest(name="Bruno")))

    assert result.ok is True
    mock_write_user.assert_called_once_with("Bruno", "")

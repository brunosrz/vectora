"""Tests TDD para get_workbench_context (FASE 2.1).

Cobre: leitura de contexto do KV, ausência de contexto, erro de workspace,
e invariante de invalidates metadata.
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from backend.tools.workspace import get_workbench_context


def _cfg(workspace_id: str = "ws1", thread_id: str = "t1") -> Any:
    return {"configurable": {"workspace_id": workspace_id, "thread_id": thread_id}}


# ---------------------------------------------------------------------------
# Sem contexto no KV
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_context_retorna_status_vazio() -> None:
    """Sem entrada no KV → status: no_context."""
    with patch("backend.tools.workspace.get_kv") as mock_get_kv:
        kv = AsyncMock()
        kv.get.return_value = None
        mock_get_kv.return_value = kv

        result = json.loads(await get_workbench_context.ainvoke({}, _cfg()))

    assert result["status"] == "no_context"
    assert "open_file" not in result or result.get("open_file") is None


# ---------------------------------------------------------------------------
# Com arquivo aberto no KV
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_com_open_file_retorna_contexto() -> None:
    """KV tem open_file → retorna contexto com arquivo."""
    ctx_data = {"open_file": "src/auth.py", "open_files": ["src/auth.py", "README.md"]}

    with patch("backend.tools.workspace.get_kv") as mock_get_kv:
        kv = AsyncMock()
        kv.get.return_value = json.dumps(ctx_data)
        mock_get_kv.return_value = kv

        result = json.loads(await get_workbench_context.ainvoke({}, _cfg()))

    assert result["status"] == "success"
    assert result["open_file"] == "src/auth.py"
    assert "README.md" in result["open_files"]


# ---------------------------------------------------------------------------
# Workspace_id vem do config quando não passado explicitamente
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_workspace_id_lido_do_config() -> None:
    """workspace_id do configurable é usado como chave no KV."""
    with patch("backend.tools.workspace.get_kv") as mock_get_kv:
        kv = AsyncMock()
        kv.get.return_value = None
        mock_get_kv.return_value = kv

        await get_workbench_context.ainvoke({}, _cfg(workspace_id="myws"))

        kv.get.assert_awaited_once()
        call_key = kv.get.call_args[0][0]
        assert "myws" in call_key


# ---------------------------------------------------------------------------
# KV com dados corrompidos → erro não propaga
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_kv_corrompido_retorna_erro_tipado() -> None:
    """JSON inválido no KV → resposta de erro em vez de exception."""
    with patch("backend.tools.workspace.get_kv") as mock_get_kv:
        kv = AsyncMock()
        kv.get.return_value = "not-valid-json{{{"
        mock_get_kv.return_value = kv

        result = json.loads(await get_workbench_context.ainvoke({}, _cfg()))

    assert result["status"] == "error"


# ---------------------------------------------------------------------------
# Metadata invariantes
# ---------------------------------------------------------------------------


def test_get_workbench_context_nao_e_destrutiva() -> None:
    extras = getattr(get_workbench_context, "extras", {}) or {}
    assert extras.get("destructive") is False


def test_get_workbench_context_categoria_workbench() -> None:
    extras = getattr(get_workbench_context, "extras", {}) or {}
    assert extras.get("category") == "workspace"

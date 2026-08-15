"""Tests para namespace de memória com workspace."""

from __future__ import annotations

from backend.tools.context import ToolContext
from backend.tools.memory import _user_id_from_ctx

# ---------------------------------------------------------------------------
# _user_id_from_ctx
# ---------------------------------------------------------------------------


def test_workspace_namespace_when_workspace_id_present():
    """workspace_id presente → namespace workspace_<id>."""
    ctx = ToolContext(workspace_id="abc12345", thread_id="001")
    assert _user_id_from_ctx(ctx) == "workspace_abc12345"


def test_session_namespace_fallback_no_workspace_id():
    """Sem workspace_id → fallback para session_<thread_id>."""
    ctx = ToolContext(thread_id="001")
    assert _user_id_from_ctx(ctx) == "session_001"


def test_default_session_when_ctx_bare():
    """ctx sem nenhum identificador → "local"."""
    assert _user_id_from_ctx(ToolContext()) == "local"


def test_workspace_takes_priority_over_thread_id():
    """workspace_id tem prioridade sobre thread_id."""
    ctx = ToolContext(workspace_id="ws001", thread_id="t999")
    result = _user_id_from_ctx(ctx)
    assert result == "workspace_ws001"
    assert "t999" not in result

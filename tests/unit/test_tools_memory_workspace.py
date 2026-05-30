"""Tests para namespace de memória com workspace (B3/B7)."""

from __future__ import annotations

from typing import Any

import pytest

from vectora.tools.memory import _user_id_from_config

# ---------------------------------------------------------------------------
# _user_id_from_config
# ---------------------------------------------------------------------------


def test_workspace_namespace_when_workspace_id_present():
    """workspace_id presente → namespace workspace_<id>."""
    config: Any = {"configurable": {"workspace_id": "abc12345", "thread_id": "001"}}
    assert _user_id_from_config(config) == "workspace_abc12345"


def test_session_namespace_fallback_no_workspace_id():
    """Sem workspace_id → fallback para session_<thread_id>."""
    config: Any = {"configurable": {"thread_id": "001"}}
    assert _user_id_from_config(config) == "session_001"


def test_default_session_when_config_none():
    """Config None → default_session."""
    assert _user_id_from_config(None) == "default_session"


def test_default_session_when_no_thread_id_or_workspace():
    """Sem thread_id nem workspace_id → default_session."""
    config: Any = {"configurable": {}}
    assert _user_id_from_config(config) == "default_session"


def test_workspace_takes_priority_over_thread_id():
    """workspace_id tem prioridade sobre thread_id."""
    config: Any = {"configurable": {"workspace_id": "ws001", "thread_id": "t999"}}
    result = _user_id_from_config(config)
    assert result == "workspace_ws001"
    assert "t999" not in result

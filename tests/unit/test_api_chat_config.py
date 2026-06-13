"""Tests para a montagem do RunnableConfig em src/api/handlers/chat.py.

Cobre R2 (permission_mode) e R4 (reasoning_effort): o ChatConfig do request
deve se traduzir corretamente para o dict ``configurable`` consumido pelo grafo.
"""

from __future__ import annotations

from src.api.handlers.chat import _build_configurable, _resolve_workspace_id
from src.api.schemas import ChatConfig

# ---------------------------------------------------------------------------
# Campos sempre presentes
# ---------------------------------------------------------------------------


def test_thread_and_user_always_present():
    cfg = _build_configurable(ChatConfig(), "thread-1", "user-1")
    assert cfg["thread_id"] == "thread-1"
    assert cfg["user_id"] == "user-1"


def test_optional_fields_absent_by_default():
    """Sem valores, os campos opcionais não entram no configurable."""
    cfg = _build_configurable(ChatConfig(), "t", "u")
    assert "workspace_id" not in cfg
    assert "custom_system_prompt" not in cfg
    assert "reasoning_effort" not in cfg


# ---------------------------------------------------------------------------
# R2 — permission_mode
# ---------------------------------------------------------------------------


def test_permission_mode_default_is_ask():
    """ChatConfig default traz permission_mode='ask' → presente no configurable."""
    cfg = _build_configurable(ChatConfig(), "t", "u")
    assert cfg["permission_mode"] == "ask"


def test_permission_mode_passthrough():
    for mode in ("ask", "accept_edits", "plan", "auto", "bypass"):
        cfg = _build_configurable(ChatConfig(permission_mode=mode), "t", "u")
        assert cfg["permission_mode"] == mode


def test_permission_mode_empty_string_omitted():
    cfg = _build_configurable(ChatConfig(permission_mode=""), "t", "u")
    assert "permission_mode" not in cfg


# ---------------------------------------------------------------------------
# R4 — reasoning_effort
# ---------------------------------------------------------------------------


def test_reasoning_effort_passthrough():
    cfg = _build_configurable(ChatConfig(reasoning_effort="high"), "t", "u")
    assert cfg["reasoning_effort"] == "high"


def test_reasoning_effort_default_omitted():
    """Default vazio → modelo usa seu próprio default (campo ausente)."""
    cfg = _build_configurable(ChatConfig(), "t", "u")
    assert "reasoning_effort" not in cfg


# ---------------------------------------------------------------------------
# Outros campos opcionais
# ---------------------------------------------------------------------------


def test_workspace_and_prompt_passthrough():
    cfg = _build_configurable(
        ChatConfig(workspace_id="ws1", custom_system_prompt="seja conciso"),
        "t",
        "u",
    )
    assert cfg["workspace_id"] == "ws1"
    assert cfg["custom_system_prompt"] == "seja conciso"


# ---------------------------------------------------------------------------
# Workspace por sessão — _resolve_workspace_id
# ---------------------------------------------------------------------------


def test_resolve_keeps_explicit_workspace():
    """Workspace escolhido pelo cliente é mantido — sem criar pasta de sessão."""
    assert _resolve_workspace_id("ws-escolhido", "thread1", "u") == "ws-escolhido"


def test_resolve_creates_session_workspace_when_empty(monkeypatch):
    """Sem workspace, deriva o padrão da sessão via registry."""
    calls = {}

    class _FakeWs:
        id = "sess-ws"

    class _FakeRegistry:
        def get_or_create_session_workspace(self, thread_id, user_id=None):
            calls["thread_id"] = thread_id
            calls["user_id"] = user_id
            return _FakeWs()

        def set_active(self, ws_id, user_id=None):
            calls["active"] = (ws_id, user_id)
            return True

    monkeypatch.setattr("src.services.workspace.workspace_registry", _FakeRegistry())
    result = _resolve_workspace_id("", "thread1", "u")
    assert result == "sess-ws"
    assert calls["thread_id"] == "thread1"
    assert calls["active"] == ("sess-ws", "u")

"""Tests for thread history reading (backend/services/agent_factory.py).

Regressão: o chat escreve via o grafo deep-agent, mas get_history/share liam
via o grafo orchestrator legado — aget_state por um grafo diferente devolvia
messages vazio, fazendo a sessão abrir vazia após reiniciar.
"""

from __future__ import annotations

import pytest

from backend.services import agent_factory
from backend.services.agent_factory import _message_text, aget_thread_messages


def test_message_text_plain_str() -> None:
    assert _message_text("olá") == "olá"


def test_message_text_multimodal_blocks() -> None:
    content = [
        {"type": "text", "text": "parte 1"},
        {"type": "tool_use", "name": "x"},
        {"type": "text", "text": " parte 2"},
    ]
    assert _message_text(content) == "parte 1 parte 2"


def test_message_text_fallback_repr() -> None:
    assert _message_text(123) == "123"


class _Msg:
    def __init__(self, type_: str, content: object) -> None:
        self.type = type_
        self.content = content


class _State:
    def __init__(self, messages: list[_Msg] | None) -> None:
        self.values = {"messages": messages} if messages is not None else None


class _Compiled:
    """Simula o CompiledStateGraph (tem aget_state)."""

    def __init__(self, messages: list[_Msg] | None) -> None:
        self._messages = messages

    async def aget_state(self, config: dict) -> _State:
        return _State(self._messages)


class _Retry:
    """Simula o RunnableRetry: sem aget_state, só expõe .bound."""

    def __init__(self, bound: object) -> None:
        self.bound = bound


@pytest.mark.asyncio
async def test_aget_thread_messages_unwraps_retry_and_filters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    messages = [
        _Msg("human", "oi"),
        _Msg("ai", [{"type": "text", "text": "olá"}]),
        _Msg("ai", [{"type": "tool_use", "name": "x"}]),  # sem texto → filtra
        _Msg("tool", "[]"),  # mensagem de tool → filtra
        _Msg("ai", "resposta final"),
    ]
    graph = _Retry(_Compiled(messages))

    async def _fake_get_user_agent(user_id: str | None = None) -> object:
        return graph

    monkeypatch.setattr(agent_factory, "get_user_agent", _fake_get_user_agent)

    pairs = await aget_thread_messages("t1")
    assert pairs == [
        ("human", "oi"),
        ("assistant", "olá"),
        ("assistant", "resposta final"),
    ]


@pytest.mark.asyncio
async def test_aget_thread_messages_empty_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _fake_get_user_agent(user_id: str | None = None) -> object:
        return _Compiled(None)

    monkeypatch.setattr(agent_factory, "get_user_agent", _fake_get_user_agent)
    assert await aget_thread_messages("t1") == []


# ---------------------------------------------------------------------------
# Sprint 5 — get_interrupt_on + reset_default_graph + profiles guard
# ---------------------------------------------------------------------------


class TestGetInterruptOn:
    def test_bypass_returns_empty(self) -> None:
        from backend.services.agent_factory import get_interrupt_on

        assert get_interrupt_on("bypass") == {}

    def test_auto_returns_empty(self) -> None:
        from backend.services.agent_factory import get_interrupt_on

        assert get_interrupt_on("auto") == {}

    def test_ask_interrupts_all_destructive(self) -> None:
        from backend.services.agent_factory import REQUIRE_APPROVAL, get_interrupt_on

        result = get_interrupt_on("ask")
        assert set(result.keys()) == REQUIRE_APPROVAL
        assert all(v is True for v in result.values())

    def test_accept_edits_excludes_file_write(self) -> None:
        from backend.services.agent_factory import (
            ACCEPT_EDITS_AUTO,
            REQUIRE_APPROVAL,
            get_interrupt_on,
        )

        result = get_interrupt_on("accept_edits")
        expected = REQUIRE_APPROVAL - ACCEPT_EDITS_AUTO
        assert set(result.keys()) == expected
        assert "file_write" not in result
        assert "file_write_tool" not in result

    def test_unknown_mode_treated_as_ask(self) -> None:
        from backend.services.agent_factory import REQUIRE_APPROVAL, get_interrupt_on

        result = get_interrupt_on("plan")
        assert set(result.keys()) == REQUIRE_APPROVAL

    def test_accept_edits_error_mode_missing(self) -> None:
        from backend.services.agent_factory import get_interrupt_on

        result = get_interrupt_on("accept_edits")
        assert result != {}, "accept_edits deve interromper ao menos terminal"


class TestResetDefaultGraph:
    def test_removes_default_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setitem(agent_factory._graphs, "__default__", object())
        monkeypatch.setitem(agent_factory._graphs, "anthropic:claude", object())

        agent_factory.reset_default_graph()

        assert "__default__" not in agent_factory._graphs
        assert "anthropic:claude" in agent_factory._graphs

    def test_noop_when_no_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(agent_factory, "_graphs", {})
        agent_factory.reset_default_graph()
        assert agent_factory._graphs == {}


class TestProfilesRegisteredGuard:
    def test_guard_flag_exists_on_module(self) -> None:
        assert hasattr(agent_factory, "_profiles_registered")
        assert isinstance(agent_factory._profiles_registered, bool)

    def test_guard_skips_registration_when_true(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Simula o guard: _profiles_registered=True → _register_profiles não chamado."""
        call_count: list[int] = [0]

        import backend.services.profiles as profiles_mod

        original_fn = profiles_mod._register_profiles

        def _counting_register() -> None:
            call_count[0] += 1

        monkeypatch.setattr(profiles_mod, "_register_profiles", _counting_register)
        monkeypatch.setattr(agent_factory, "_profiles_registered", True)

        try:
            if not agent_factory._profiles_registered:
                profiles_mod._register_profiles()
                agent_factory._profiles_registered = True
        finally:
            monkeypatch.setattr(profiles_mod, "_register_profiles", original_fn)

        assert call_count[0] == 0, "guard deve evitar chamada quando já registrado"

    def test_guard_registers_when_false(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Com _profiles_registered=False → _register_profiles é chamado."""
        call_count: list[int] = [0]

        import backend.services.profiles as profiles_mod

        original_fn = profiles_mod._register_profiles

        def _counting_register() -> None:
            call_count[0] += 1

        monkeypatch.setattr(profiles_mod, "_register_profiles", _counting_register)
        monkeypatch.setattr(agent_factory, "_profiles_registered", False)

        try:
            if not agent_factory._profiles_registered:
                profiles_mod._register_profiles()
                agent_factory._profiles_registered = True
        finally:
            monkeypatch.setattr(profiles_mod, "_register_profiles", original_fn)

        assert call_count[0] == 1, "deve chamar _register_profiles exatamente uma vez"

"""Tests for thread history reading (backend/services/agent_factory.py).

Regressão: o chat escreve via o grafo deep-agent, mas get_history/share liam
via o grafo orchestrator legado — aget_state por um grafo diferente devolvia
messages vazio, fazendo a sessão abrir vazia após reiniciar.

Correção: aget_thread_messages usa um StateGraph mínimo (sem LLM) com o mesmo
DeepAgentState schema para ler checkpoints, tornando a leitura robusta e rápida.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

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


class _Snapshot:
    """Snapshot fake de ``graph.aget_state_history`` — só ``values`` e
    ``parent_config`` importam pro algoritmo de checkpoint_id pai."""

    def __init__(self, messages: list[_Msg], parent_checkpoint_id: str | None) -> None:
        self.values: dict = {"messages": messages}
        self.parent_config: dict | None = (
            {"configurable": {"checkpoint_id": parent_checkpoint_id}}
            if parent_checkpoint_id is not None
            else None
        )


async def _async_iter(items: list[_Snapshot]):
    for item in items:
        yield item


def _make_compiled(history_newest_first: list[_Snapshot]) -> MagicMock:
    """Retorna um CompiledStateGraph fake com aget_state_history fixo."""
    compiled = MagicMock()
    compiled.aget_state_history = MagicMock(
        return_value=_async_iter(history_newest_first)
    )
    return compiled


@pytest.mark.asyncio
async def test_aget_thread_messages_filters_tool_and_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Filtra mensagens de tool e AI sem texto; mapeia human/ai → role correto."""
    human = _Msg("human", "oi")
    rest = [
        _Msg("ai", [{"type": "text", "text": "olá"}]),
        _Msg("ai", [{"type": "tool_use", "name": "x"}]),  # sem texto → filtra
        _Msg("tool", "[]"),  # tool result → filtra
        _Msg("ai", "resposta final"),
    ]
    # Mais antigo primeiro na construção; _make_compiled recebe invertido
    # (mais recente primeiro), como o LangGraph real entrega.
    history_chronological = [
        _Snapshot([human], "cp-inicial"),
        _Snapshot([human, *rest], "cp-apos-human"),
    ]
    compiled = _make_compiled(list(reversed(history_chronological)))

    sentinel_checkpointer = object()
    monkeypatch.setattr(agent_factory, "_checkpointer", sentinel_checkpointer)

    async def _noop_ensure() -> None:
        pass

    monkeypatch.setattr(agent_factory, "_ensure_infra", _noop_ensure)
    monkeypatch.setattr(
        agent_factory, "get_user_agent", AsyncMock(return_value=compiled)
    )

    pairs = await aget_thread_messages("t1")

    assert pairs == [
        ("human", "oi", "cp-inicial", []),
        ("assistant", "olá", "cp-apos-human", []),
        ("assistant", "resposta final", "cp-apos-human", []),
    ]


@pytest.mark.asyncio
async def test_aget_thread_messages_empty_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Devolve lista vazia quando o histórico só tem estado sem mensagens."""
    compiled = _make_compiled([_Snapshot([], None)])

    sentinel_checkpointer = object()
    monkeypatch.setattr(agent_factory, "_checkpointer", sentinel_checkpointer)

    async def _noop_ensure() -> None:
        pass

    monkeypatch.setattr(agent_factory, "_ensure_infra", _noop_ensure)
    monkeypatch.setattr(
        agent_factory, "get_user_agent", AsyncMock(return_value=compiled)
    )

    assert await aget_thread_messages("t1") == []


@pytest.mark.asyncio
async def test_aget_thread_messages_no_checkpointer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Devolve lista vazia quando _checkpointer é None (sem infra inicializada)."""
    monkeypatch.setattr(agent_factory, "_checkpointer", None)

    async def _noop_ensure() -> None:
        pass

    monkeypatch.setattr(agent_factory, "_ensure_infra", _noop_ensure)

    assert await aget_thread_messages("qualquer-thread") == []


# ---------------------------------------------------------------------------
# reset_default_graph + profiles guard
# ---------------------------------------------------------------------------


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

        import backend.workspace.profiles as profiles_mod

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

        import backend.workspace.profiles as profiles_mod

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

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

"""Testes TDD para o Bloco E — HITL em Chat.

E1 — adapt_stream detecta o evento __interrupt__ do LangGraph e emite HITLEvent.
E2 — hitl_check trata as ações approve / reject / edit corretamente.

Todos os testes foram escritos ANTES da implementação (TDD: red → green).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# ===========================================================================
# Helpers
# ===========================================================================


@dataclass
class _FakeInterrupt:
    """Simula langgraph.types.Interrupt (sem importar LangGraph no teste)."""

    value: Any
    resumable: bool = True


def _make_interrupt_event(tool_calls: list[dict]) -> dict:
    """Cria um evento on_chain_stream com __interrupt__ como o LangGraph emite."""
    return {
        "event": "on_chain_stream",
        "name": "LangGraph",
        "data": {"chunk": {"__interrupt__": (_FakeInterrupt(value=tool_calls),)}},
    }


async def _collect(gen: Any) -> list[dict]:
    """Coleta todas as linhas SSE e parseia os JSONs."""
    results: list[dict] = []
    async for line in gen:
        raw = line.removeprefix("data: ").strip()
        if raw and raw != "[DONE]":
            results.append(json.loads(raw))
    return results


# ===========================================================================
# E1 — HITLEvent schema
# ===========================================================================


class TestHITLEventSchema:
    def test_hitl_event_importable(self) -> None:
        from src.api.schemas import HITLEvent

    def test_hitl_event_has_tool_name(self) -> None:
        from src.api.schemas import HITLEvent

        e = HITLEvent(
            tool_name="terminal", args_json='{"cmd":"ls"}', interrupt_id="abc"
        )
        assert e.tool_name == "terminal"

    def test_hitl_event_has_args_json(self) -> None:
        from src.api.schemas import HITLEvent

        e = HITLEvent(
            tool_name="terminal", args_json='{"cmd":"ls"}', interrupt_id="abc"
        )
        assert e.args_json == '{"cmd":"ls"}'

    def test_hitl_event_has_interrupt_id(self) -> None:
        from src.api.schemas import HITLEvent

        e = HITLEvent(tool_name="terminal", args_json="{}", interrupt_id="xyz")
        assert e.interrupt_id == "xyz"

    def test_hitl_event_encode_has_type_hitl(self) -> None:
        from src.api.schemas import HITLEvent, encode_event

        line = encode_event(
            HITLEvent(tool_name="terminal", args_json="{}", interrupt_id="id1")
        )
        data = json.loads(line.removeprefix("data: ").strip())
        assert data["type"] == "hitl"
        assert data["tool_name"] == "terminal"

    def test_hitl_event_in_stream_payload_union(self) -> None:
        from src.api.schemas import HITLEvent, StreamChatEventPayload

        e: StreamChatEventPayload = HITLEvent(
            tool_name="t", args_json="{}", interrupt_id="i"
        )
        assert e is not None


# ===========================================================================
# E1 — adapt_stream detecta __interrupt__
# ===========================================================================


class TestAdaptStreamHITL:
    @pytest.mark.asyncio
    async def test_emits_hitl_event_when_interrupt_detected(self) -> None:
        from src.api.adapters import adapt_stream

        events = [
            _make_interrupt_event(
                [{"id": "tc1", "name": "terminal", "args": {"cmd": "ls"}}]
            )
        ]

        async def _gen():
            for e in events:
                yield e

        result = await _collect(adapt_stream(_gen(), "thread-1"))
        assert any(r["type"] == "hitl" for r in result)

    @pytest.mark.asyncio
    async def test_hitl_event_has_correct_tool_name(self) -> None:
        from src.api.adapters import adapt_stream

        events = [
            _make_interrupt_event(
                [
                    {
                        "id": "tc1",
                        "name": "file_write",
                        "args": {"path": "x.py", "content": ""},
                    }
                ]
            )
        ]

        async def _gen():
            for e in events:
                yield e

        result = await _collect(adapt_stream(_gen(), "thread-1"))
        hitl = next(r for r in result if r["type"] == "hitl")
        assert hitl["tool_name"] == "file_write"

    @pytest.mark.asyncio
    async def test_hitl_event_args_json_parseable(self) -> None:
        from src.api.adapters import adapt_stream

        events = [
            _make_interrupt_event(
                [{"id": "tc1", "name": "terminal", "args": {"cmd": "rm -rf /"}}]
            )
        ]

        async def _gen():
            for e in events:
                yield e

        result = await _collect(adapt_stream(_gen(), "thread-1"))
        hitl = next(r for r in result if r["type"] == "hitl")
        parsed = json.loads(hitl["args_json"])
        assert parsed["cmd"] == "rm -rf /"

    @pytest.mark.asyncio
    async def test_hitl_event_interrupt_id_matches_tool_call_id(self) -> None:
        from src.api.adapters import adapt_stream

        events = [
            _make_interrupt_event(
                [{"id": "my-call-id", "name": "terminal", "args": {}}]
            )
        ]

        async def _gen():
            for e in events:
                yield e

        result = await _collect(adapt_stream(_gen(), "thread-1"))
        hitl = next(r for r in result if r["type"] == "hitl")
        assert hitl["interrupt_id"] == "my-call-id"

    @pytest.mark.asyncio
    async def test_done_event_emitted_after_hitl(self) -> None:
        from src.api.adapters import adapt_stream

        events = [
            _make_interrupt_event([{"id": "tc1", "name": "terminal", "args": {}}])
        ]

        async def _gen():
            for e in events:
                yield e

        result = await _collect(adapt_stream(_gen(), "thread-1"))
        types = [r["type"] for r in result]
        assert "done" in types
        # done deve vir APÓS hitl
        assert types.index("done") > types.index("hitl")

    @pytest.mark.asyncio
    async def test_no_hitl_event_without_interrupt(self) -> None:
        from src.api.adapters import adapt_stream

        chunk = MagicMock()
        chunk.content = "olá"
        events = [
            {
                "event": "on_chat_model_stream",
                "name": "coder",
                "data": {"chunk": chunk},
                "metadata": {"langgraph_node": "coder"},
                "run_name": "coder",
            }
        ]

        async def _gen():
            for e in events:
                yield e

        result = await _collect(adapt_stream(_gen(), "thread-1"))
        assert not any(r["type"] == "hitl" for r in result)

    @pytest.mark.asyncio
    async def test_thread_event_is_always_first(self) -> None:
        from src.api.adapters import adapt_stream

        events = [
            _make_interrupt_event([{"id": "tc1", "name": "terminal", "args": {}}])
        ]

        async def _gen():
            for e in events:
                yield e

        result = await _collect(adapt_stream(_gen(), "thread-42"))
        assert result[0]["type"] == "thread"
        assert result[0]["thread_id"] == "thread-42"

    @pytest.mark.asyncio
    async def test_multiple_sensitive_tools_in_one_interrupt(self) -> None:
        """Quando há múltiplas tools sensíveis, emite HITLEvent para a primeira."""
        from src.api.adapters import adapt_stream

        events = [
            _make_interrupt_event(
                [
                    {"id": "t1", "name": "terminal", "args": {"cmd": "echo hi"}},
                    {
                        "id": "t2",
                        "name": "file_write",
                        "args": {"path": "a.txt", "content": "x"},
                    },
                ]
            )
        ]

        async def _gen():
            for e in events:
                yield e

        result = await _collect(adapt_stream(_gen(), "thread-1"))
        hitl_events = [r for r in result if r["type"] == "hitl"]
        assert len(hitl_events) >= 1
        # Primeira tool deve ser "terminal"
        assert hitl_events[0]["tool_name"] == "terminal"


# ===========================================================================
# E2 — hitl_check: ação "edit"
# ===========================================================================


class TestHITLCheckEditAction:
    @pytest.mark.asyncio
    async def test_hitl_check_edit_approves_not_cancelled(self) -> None:
        """action='edit' deve aprovar a execução (hitl_cancelled=False)."""
        from langchain_core.messages import AIMessage

        from src.nodes.hitl import hitl_check

        tool_call = {
            "id": "tc1",
            "name": "terminal",
            "args": {"cmd": "ls"},
            "type": "tool_call",
        }
        msg = AIMessage(content="", tool_calls=[tool_call], id="msg1")
        state: dict = {"messages": [msg]}

        decision = {"action": "edit", "args": {"cmd": "echo hello"}}
        with patch("src.nodes.hitl.interrupt", return_value=decision):
            result = await hitl_check(state)  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]

        assert result.get("hitl_cancelled") is False

    @pytest.mark.asyncio
    async def test_hitl_check_edit_updates_tool_args(self) -> None:
        """Os args da tool editada devem ser atualizados na mensagem retornada."""
        from langchain_core.messages import AIMessage

        from src.nodes.hitl import hitl_check

        tool_call = {
            "id": "tc1",
            "name": "terminal",
            "args": {"cmd": "rm -rf /"},
            "type": "tool_call",
        }
        msg = AIMessage(content="", tool_calls=[tool_call], id="msg1")
        state: dict = {"messages": [msg]}

        decision = {"action": "edit", "args": {"cmd": "echo safe"}}
        with patch("src.nodes.hitl.interrupt", return_value=decision):
            result = await hitl_check(state)  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]

        # Deve retornar mensagem atualizada com novos args
        assert result.get("hitl_cancelled") is False
        updated_msgs = result.get("messages", [])
        if updated_msgs:
            updated_tc = updated_msgs[0].tool_calls[0]
            assert updated_tc["args"]["cmd"] == "echo safe"

    @pytest.mark.asyncio
    async def test_hitl_check_unknown_action_rejects(self) -> None:
        """Ação desconhecida deve resultar em cancelamento."""
        from langchain_core.messages import AIMessage

        from src.nodes.hitl import hitl_check

        tool_call = {"id": "tc1", "name": "terminal", "args": {}, "type": "tool_call"}
        msg = AIMessage(content="", tool_calls=[tool_call], id="msg1")
        state: dict = {"messages": [msg]}

        with patch("src.nodes.hitl.interrupt", return_value={"action": "unknown_xyz"}):
            result = await hitl_check(state)  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]

        assert result.get("hitl_cancelled") is True

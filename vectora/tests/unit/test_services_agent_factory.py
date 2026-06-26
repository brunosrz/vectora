"""Testes para backend/services/agent_factory.py.

Cobre: aget_thread_messages — bug crítico onde o histórico não era
restaurado após restart (grafo NOOP não desserializa estado do deepagents).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ─────────────────────────── helpers ─────────────────────────────────────────


def _make_msg(type_: str, content: str) -> MagicMock:
    msg = MagicMock()
    msg.type = type_
    msg.content = content
    return msg


def _make_state(messages: list[Any]) -> MagicMock:
    state = MagicMock()
    state.values = {"messages": messages}
    return state


# ─────────────────────────── aget_thread_messages ────────────────────────────


class TestAgetThreadMessages:
    @pytest.mark.asyncio
    async def test_no_checkpointer_returns_empty(self):
        import backend.services.agent_factory as af

        original = af._checkpointer
        af._checkpointer = None
        try:
            result = await af.aget_thread_messages("thread-abc")
        finally:
            af._checkpointer = original

        assert result == []

    @pytest.mark.asyncio
    async def test_empty_state_returns_empty(self):
        import backend.services.agent_factory as af

        empty_state = MagicMock()
        empty_state.values = {}

        mock_graph = AsyncMock()
        mock_graph.aget_state = AsyncMock(return_value=empty_state)

        with (
            patch.object(af, "_checkpointer", MagicMock()),
            patch.object(af, "_ensure_infra", AsyncMock()),
            patch.object(af, "get_user_agent", AsyncMock(return_value=mock_graph)),
        ):
            result = await af.aget_thread_messages("thread-empty")

        assert result == []

    @pytest.mark.asyncio
    async def test_none_state_returns_empty(self):
        import backend.services.agent_factory as af

        mock_graph = AsyncMock()
        mock_graph.aget_state = AsyncMock(return_value=None)

        with (
            patch.object(af, "_checkpointer", MagicMock()),
            patch.object(af, "_ensure_infra", AsyncMock()),
            patch.object(af, "get_user_agent", AsyncMock(return_value=mock_graph)),
        ):
            result = await af.aget_thread_messages("thread-none")

        assert result == []

    @pytest.mark.asyncio
    async def test_human_and_ai_messages_returned(self):
        import backend.services.agent_factory as af

        state = _make_state(
            [
                _make_msg("human", "Olá Vectora"),
                _make_msg("ai", "Olá! Como posso ajudar?"),
            ]
        )
        mock_graph = AsyncMock()
        mock_graph.aget_state = AsyncMock(return_value=state)

        with (
            patch.object(af, "_checkpointer", MagicMock()),
            patch.object(af, "_ensure_infra", AsyncMock()),
            patch.object(af, "get_user_agent", AsyncMock(return_value=mock_graph)),
        ):
            result = await af.aget_thread_messages("thread-ok")

        assert result == [
            ("human", "Olá Vectora"),
            ("assistant", "Olá! Como posso ajudar?"),
        ]

    @pytest.mark.asyncio
    async def test_tool_messages_filtered_out(self):
        import backend.services.agent_factory as af

        state = _make_state(
            [
                _make_msg("human", "Execute o teste"),
                _make_msg("tool", '{"result": "ok"}'),
                _make_msg("ai", "Teste executado."),
            ]
        )
        mock_graph = AsyncMock()
        mock_graph.aget_state = AsyncMock(return_value=state)

        with (
            patch.object(af, "_checkpointer", MagicMock()),
            patch.object(af, "_ensure_infra", AsyncMock()),
            patch.object(af, "get_user_agent", AsyncMock(return_value=mock_graph)),
        ):
            result = await af.aget_thread_messages("thread-tool")

        roles = [r for r, _ in result]
        assert "tool" not in roles
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_ai_messages_without_text_filtered(self):
        import backend.services.agent_factory as af

        state = _make_state(
            [
                _make_msg("human", "faz algo"),
                _make_msg("ai", ""),  # só tool-call, sem texto
                _make_msg("ai", "Feito!"),
            ]
        )
        mock_graph = AsyncMock()
        mock_graph.aget_state = AsyncMock(return_value=state)

        with (
            patch.object(af, "_checkpointer", MagicMock()),
            patch.object(af, "_ensure_infra", AsyncMock()),
            patch.object(af, "get_user_agent", AsyncMock(return_value=mock_graph)),
        ):
            result = await af.aget_thread_messages("thread-notool")

        assert ("assistant", "") not in result
        assert ("assistant", "Feito!") in result

    @pytest.mark.asyncio
    async def test_aget_state_exception_returns_empty(self):
        import backend.services.agent_factory as af

        mock_graph = AsyncMock()
        mock_graph.aget_state = AsyncMock(side_effect=RuntimeError("db error"))

        with (
            patch.object(af, "_checkpointer", MagicMock()),
            patch.object(af, "_ensure_infra", AsyncMock()),
            patch.object(af, "get_user_agent", AsyncMock(return_value=mock_graph)),
        ):
            result = await af.aget_thread_messages("thread-err")

        assert result == []

    @pytest.mark.asyncio
    async def test_multipart_content_extracted(self):
        import backend.services.agent_factory as af

        msg = MagicMock()
        msg.type = "ai"
        msg.content = [
            {"type": "text", "text": "Parte 1"},
            {"type": "text", "text": " Parte 2"},
        ]
        state = _make_state([msg])
        mock_graph = AsyncMock()
        mock_graph.aget_state = AsyncMock(return_value=state)

        with (
            patch.object(af, "_checkpointer", MagicMock()),
            patch.object(af, "_ensure_infra", AsyncMock()),
            patch.object(af, "get_user_agent", AsyncMock(return_value=mock_graph)),
        ):
            result = await af.aget_thread_messages("thread-multi")

        assert result == [("assistant", "Parte 1 Parte 2")]

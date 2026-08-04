"""Testes para backend/services/agent_factory.py.

Cobre: aget_thread_messages — bug crítico onde o histórico não era
restaurado após restart (grafo NOOP não desserializa estado do deepagents), e
o checkpoint_id pai anexado a cada mensagem (fork de checkpoint pra editar/
regenerar — Item 3 do plano de migração backend/frontend).
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
    msg.additional_kwargs = {}
    return msg


def _make_snapshot(messages: list[Any], parent_checkpoint_id: str | None) -> MagicMock:
    """Snapshot fake de ``graph.aget_state_history`` — só ``values`` e
    ``parent_config`` importam pro algoritmo (não usa ``snapshot.config``)."""
    snap = MagicMock()
    snap.values = {"messages": messages}
    snap.parent_config = (
        {"configurable": {"checkpoint_id": parent_checkpoint_id}}
        if parent_checkpoint_id is not None
        else None
    )
    return snap


async def _async_iter(items: list[Any]):
    for item in items:
        yield item


def _mock_history(chronological_steps: list[tuple[list[Any], str | None]]) -> list[Any]:
    """``chronological_steps``: ``[(messages_neste_passo, checkpoint_pai), ...]``
    em ordem cronológica (mais antigo primeiro) — cada item representa um
    snapshot cujo ``values.messages`` é a lista ACUMULADA até aquele ponto.
    Devolve invertido (mais recente primeiro), como o LangGraph real entrega.
    """
    snaps = [_make_snapshot(msgs, parent_id) for msgs, parent_id in chronological_steps]
    return list(reversed(snaps))


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
    async def test_empty_history_returns_empty(self):
        import backend.services.agent_factory as af

        mock_graph = AsyncMock()
        mock_graph.aget_state_history = MagicMock(return_value=_async_iter([]))

        with (
            patch.object(af, "_checkpointer", MagicMock()),
            patch.object(af, "_ensure_infra", AsyncMock()),
            patch.object(af, "get_user_agent", AsyncMock(return_value=mock_graph)),
        ):
            result = await af.aget_thread_messages("thread-empty")

        assert result == []

    @pytest.mark.asyncio
    async def test_history_with_only_empty_state_returns_empty(self):
        import backend.services.agent_factory as af

        history = _mock_history([([], None)])
        mock_graph = AsyncMock()
        mock_graph.aget_state_history = MagicMock(return_value=_async_iter(history))

        with (
            patch.object(af, "_checkpointer", MagicMock()),
            patch.object(af, "_ensure_infra", AsyncMock()),
            patch.object(af, "get_user_agent", AsyncMock(return_value=mock_graph)),
        ):
            result = await af.aget_thread_messages("thread-none")

        assert result == []

    @pytest.mark.asyncio
    async def test_human_and_ai_messages_returned_with_parent_checkpoint(self):
        import backend.services.agent_factory as af

        human = _make_msg("human", "Olá Vectora")
        ai = _make_msg("ai", "Olá! Como posso ajudar?")
        history = _mock_history(
            [
                ([human], "cp-inicial"),
                ([human, ai], "cp-apos-human"),
            ]
        )
        mock_graph = AsyncMock()
        mock_graph.aget_state_history = MagicMock(return_value=_async_iter(history))

        with (
            patch.object(af, "_checkpointer", MagicMock()),
            patch.object(af, "_ensure_infra", AsyncMock()),
            patch.object(af, "get_user_agent", AsyncMock(return_value=mock_graph)),
        ):
            result = await af.aget_thread_messages("thread-ok")

        assert result == [
            ("human", "Olá Vectora", "cp-inicial", []),
            ("assistant", "Olá! Como posso ajudar?", "cp-apos-human", []),
        ]

    @pytest.mark.asyncio
    async def test_message_with_no_parent_checkpoint_gets_empty_string(self):
        """Primeira mensagem da thread — o checkpoint pai é o estado inicial
        (``parent_config=None``, caso raríssimo/defensivo); vira string vazia,
        nunca None, pra HistoryMessage.checkpoint_id (campo str) aceitar."""
        import backend.services.agent_factory as af

        human = _make_msg("human", "primeira mensagem")
        history = _mock_history([([human], None)])
        mock_graph = AsyncMock()
        mock_graph.aget_state_history = MagicMock(return_value=_async_iter(history))

        with (
            patch.object(af, "_checkpointer", MagicMock()),
            patch.object(af, "_ensure_infra", AsyncMock()),
            patch.object(af, "get_user_agent", AsyncMock(return_value=mock_graph)),
        ):
            result = await af.aget_thread_messages("thread-first")

        assert result == [("human", "primeira mensagem", "", [])]

    @pytest.mark.asyncio
    async def test_tool_messages_filtered_out(self):
        import backend.services.agent_factory as af

        human = _make_msg("human", "Execute o teste")
        tool = _make_msg("tool", '{"result": "ok"}')
        ai = _make_msg("ai", "Teste executado.")
        history = _mock_history(
            [
                ([human], "cp0"),
                ([human, tool], "cp1"),
                ([human, tool, ai], "cp2"),
            ]
        )
        mock_graph = AsyncMock()
        mock_graph.aget_state_history = MagicMock(return_value=_async_iter(history))

        with (
            patch.object(af, "_checkpointer", MagicMock()),
            patch.object(af, "_ensure_infra", AsyncMock()),
            patch.object(af, "get_user_agent", AsyncMock(return_value=mock_graph)),
        ):
            result = await af.aget_thread_messages("thread-tool")

        roles = [r for r, _text, _cp, _att in result]
        assert "tool" not in roles
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_ai_messages_without_text_filtered(self):
        import backend.services.agent_factory as af

        human = _make_msg("human", "faz algo")
        ai_empty = _make_msg("ai", "")  # só tool-call, sem texto
        ai_final = _make_msg("ai", "Feito!")
        history = _mock_history(
            [
                ([human], "cp0"),
                ([human, ai_empty], "cp1"),
                ([human, ai_empty, ai_final], "cp2"),
            ]
        )
        mock_graph = AsyncMock()
        mock_graph.aget_state_history = MagicMock(return_value=_async_iter(history))

        with (
            patch.object(af, "_checkpointer", MagicMock()),
            patch.object(af, "_ensure_infra", AsyncMock()),
            patch.object(af, "get_user_agent", AsyncMock(return_value=mock_graph)),
        ):
            result = await af.aget_thread_messages("thread-notool")

        texts = [(r, t) for r, t, _cp, _att in result]
        assert ("assistant", "") not in texts
        assert ("assistant", "Feito!") in texts

    @pytest.mark.asyncio
    async def test_aget_state_history_exception_returns_empty(self):
        import backend.services.agent_factory as af

        mock_graph = AsyncMock()
        mock_graph.aget_state_history = MagicMock(side_effect=RuntimeError("db error"))

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
        msg.additional_kwargs = {}
        history = _mock_history([([msg], "cp0")])
        mock_graph = AsyncMock()
        mock_graph.aget_state_history = MagicMock(return_value=_async_iter(history))

        with (
            patch.object(af, "_checkpointer", MagicMock()),
            patch.object(af, "_ensure_infra", AsyncMock()),
            patch.object(af, "get_user_agent", AsyncMock(return_value=mock_graph)),
        ):
            result = await af.aget_thread_messages("thread-multi")

        assert result == [("assistant", "Parte 1 Parte 2", "cp0", [])]


# ─────────────────────────── aget_thread_todos ────────────────────────────
# Popula a seção "Tasks" do Plan tab num reload de página — o SSE ao vivo
# (TodosUpdatedEvent) já entrega isso, mas não persiste no client entre
# streams; lê direto do snapshot mais recente do checkpoint (fonte real).


class TestAgetThreadTodos:
    @pytest.mark.asyncio
    async def test_no_checkpointer_returns_empty(self):
        import backend.services.agent_factory as af

        original = af._checkpointer
        af._checkpointer = None
        try:
            result = await af.aget_thread_todos("thread-abc")
        finally:
            af._checkpointer = original

        assert result == []

    @pytest.mark.asyncio
    async def test_returns_todos_from_latest_snapshot(self):
        import backend.services.agent_factory as af

        todos = [{"content": "passo 1", "status": "completed"}]
        snap = MagicMock()
        snap.values = {"todos": todos}
        mock_graph = AsyncMock()
        mock_graph.aget_state = AsyncMock(return_value=snap)

        with (
            patch.object(af, "_checkpointer", MagicMock()),
            patch.object(af, "_ensure_infra", AsyncMock()),
            patch.object(af, "get_user_agent", AsyncMock(return_value=mock_graph)),
        ):
            result = await af.aget_thread_todos("thread-ok")

        assert result == todos

    @pytest.mark.asyncio
    async def test_snapshot_without_todos_key_returns_empty(self):
        """Thread que nunca chamou write_todos — chave ausente, não erro."""
        import backend.services.agent_factory as af

        snap = MagicMock()
        snap.values = {"messages": []}
        mock_graph = AsyncMock()
        mock_graph.aget_state = AsyncMock(return_value=snap)

        with (
            patch.object(af, "_checkpointer", MagicMock()),
            patch.object(af, "_ensure_infra", AsyncMock()),
            patch.object(af, "get_user_agent", AsyncMock(return_value=mock_graph)),
        ):
            result = await af.aget_thread_todos("thread-no-todos")

        assert result == []

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
            result = await af.aget_thread_todos("thread-err")

        assert result == []


class TestAgetThreadPendingInterrupt:
    """Reidratação do HITLPanel após reload de página (Sprint 38.2) — lê
    ``snapshot.tasks[*].interrupts``, não ``snapshot.values``."""

    @pytest.mark.asyncio
    async def test_no_checkpointer_returns_none(self):
        import backend.services.agent_factory as af

        original = af._checkpointer
        af._checkpointer = None
        try:
            result = await af.aget_thread_pending_interrupt("thread-abc")
        finally:
            af._checkpointer = original

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_pending_interrupt_from_snapshot_tasks(self):
        import backend.services.agent_factory as af

        intr = MagicMock()
        intr.value = [{"name": "file_write", "args": {"path": "a.py"}, "id": "intr-1"}]
        task = MagicMock()
        task.interrupts = (intr,)
        snap = MagicMock()
        snap.tasks = (task,)
        mock_graph = AsyncMock()
        mock_graph.aget_state = AsyncMock(return_value=snap)

        with (
            patch.object(af, "_checkpointer", MagicMock()),
            patch.object(af, "_ensure_infra", AsyncMock()),
            patch.object(af, "get_user_agent", AsyncMock(return_value=mock_graph)),
        ):
            result = await af.aget_thread_pending_interrupt("thread-ok")

        assert result == {
            "tool_name": "file_write",
            "args": {"path": "a.py"},
            "interrupt_id": "intr-1",
        }

    @pytest.mark.asyncio
    async def test_no_pending_task_returns_none(self):
        """Erro/borda: thread sem nenhuma pausa ativa — `tasks` vazio, não erro."""
        import backend.services.agent_factory as af

        snap = MagicMock()
        snap.tasks = ()
        mock_graph = AsyncMock()
        mock_graph.aget_state = AsyncMock(return_value=snap)

        with (
            patch.object(af, "_checkpointer", MagicMock()),
            patch.object(af, "_ensure_infra", AsyncMock()),
            patch.object(af, "get_user_agent", AsyncMock(return_value=mock_graph)),
        ):
            result = await af.aget_thread_pending_interrupt("thread-no-pending")

        assert result is None

    @pytest.mark.asyncio
    async def test_aget_state_exception_returns_none(self):
        import backend.services.agent_factory as af

        mock_graph = AsyncMock()
        mock_graph.aget_state = AsyncMock(side_effect=RuntimeError("db error"))

        with (
            patch.object(af, "_checkpointer", MagicMock()),
            patch.object(af, "_ensure_infra", AsyncMock()),
            patch.object(af, "get_user_agent", AsyncMock(return_value=mock_graph)),
        ):
            result = await af.aget_thread_pending_interrupt("thread-err")

        assert result is None

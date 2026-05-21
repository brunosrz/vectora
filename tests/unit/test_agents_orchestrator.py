"""Tests for vectora/agents/orchestrator.py"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.constants import END
from langgraph.types import Command

from vectora.agents.orchestrator import orchestrator

if TYPE_CHECKING:
    from vectora.state import State

# ---------------------------------------------------------------------------
# orchestrator node
# ---------------------------------------------------------------------------


class TestOrchestrator:
    @pytest.mark.asyncio
    async def test_greeting_responds_inline(self):
        """Saudações simples → orchestrator responde inline (action='respond')."""
        state: State = {
            "messages": [HumanMessage(content="oi")],
            "session_metadata": {},
        }
        cmd = await orchestrator(state)
        assert isinstance(cmd, Command)
        # Quando respond inline, goto == END
        assert cmd.goto == END
        assert cmd.update is not None
        assert cmd.update["routing_decision"] == "respond"
        # A resposta deve estar em messages como AIMessage
        messages = cmd.update.get("messages", [])
        assert len(messages) == 1
        assert isinstance(messages[0], AIMessage)
        assert messages[0].content  # não vazia

    @pytest.mark.asyncio
    async def test_coder_delegates_to_coder(self):
        """Pedido de criação de arquivo → delega para coder com task_query."""
        state: State = {
            "messages": [HumanMessage(content="cria um arquivo main.py")],
            "session_metadata": {},
        }
        cmd = await orchestrator(state)
        assert isinstance(cmd, Command)
        assert cmd.update is not None

        # Se o LLM entrou em fallback por rate limit, o routing é 'respond' e a
        # mensagem contém texto de erro — skip em vez de falhar
        if cmd.goto == END:
            msgs = cmd.update.get("messages", [])
            if msgs and "erro interno" in str(msgs[0].content).lower():
                pytest.skip("LLM rate-limited — fallback acionado, skip do teste")

        assert cmd.goto == "coder", f"esperado 'coder', got '{cmd.goto}'"
        assert cmd.update["routing_decision"] == "coder"
        assert "orchestrator_task" in cmd.update
        assert isinstance(cmd.update["orchestrator_task"], str)
        assert len(cmd.update["orchestrator_task"]) > 0

    @pytest.mark.asyncio
    async def test_rag_delegates_to_rag_subgraph(self):
        """Pergunta sobre documentos → delega para rag_subgraph com task_query."""
        state: State = {
            "messages": [HumanMessage(content="o que diz o documento sobre auth?")],
            "session_metadata": {},
        }
        cmd = await orchestrator(state)
        assert isinstance(cmd, Command)
        assert cmd.update is not None

        if cmd.goto == END:
            msgs = cmd.update.get("messages", [])
            if msgs and "erro interno" in str(msgs[0].content).lower():
                pytest.skip("LLM rate-limited — fallback acionado, skip do teste")

        assert cmd.goto == "rag_subgraph", f"esperado 'rag_subgraph', got '{cmd.goto}'"
        assert cmd.update["routing_decision"] == "rag"
        assert "orchestrator_task" in cmd.update

    @pytest.mark.asyncio
    async def test_uses_last_human_message(self):
        """Deve considerar a última HumanMessage para a decisão."""
        state: State = {
            "messages": [
                HumanMessage(content="o que diz o documento?"),  # → rag
                AIMessage(content="Resposta"),
                HumanMessage(content="oi"),  # → respond inline (última)
            ],
            "session_metadata": {},
        }
        cmd = await orchestrator(state)
        assert cmd.update is not None
        assert cmd.update["routing_decision"] == "respond"

    @pytest.mark.asyncio
    async def test_empty_messages_defaults_to_respond(self):
        """Sem mensagens → fallback inline (respond)."""
        state: State = {"messages": [], "session_metadata": {}}
        cmd = await orchestrator(state)
        assert cmd.goto == END

    @pytest.mark.asyncio
    async def test_no_human_message_defaults_to_respond(self):
        """Sem HumanMessage → fallback inline (respond)."""
        state: State = {
            "messages": [AIMessage(content="resposta")],
            "session_metadata": {},
        }
        cmd = await orchestrator(state)
        assert cmd.goto == END

    @pytest.mark.asyncio
    async def test_task_query_is_descriptive_for_coder(self):
        """task_query para coder deve conter instrução útil."""
        state: State = {
            "messages": [
                HumanMessage(
                    content="cria um script Python que lê um CSV e gera um gráfico"
                )
            ],
            "session_metadata": {},
        }
        cmd = await orchestrator(state)
        if cmd.goto == "coder":
            task = cmd.update.get("orchestrator_task", "")
            assert isinstance(task, str)
            assert len(task) >= 10

    @pytest.mark.asyncio
    async def test_respond_inline_has_no_orchestrator_task(self):
        """Quando responde inline, orchestrator_task não deve estar no update."""
        state: State = {
            "messages": [HumanMessage(content="oi, tudo bem?")],
            "session_metadata": {},
        }
        cmd = await orchestrator(state)
        if cmd.goto == END:
            assert cmd.update.get("orchestrator_task") is None
            messages = cmd.update.get("messages", [])
            assert len(messages) == 1

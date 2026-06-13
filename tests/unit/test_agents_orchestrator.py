<<<<<<< HEAD
"""Tests for vectora/agents/orchestrator.py"""
=======
"""Tests for src/agents/orchestrator.py"""
>>>>>>> dev

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
<<<<<<< HEAD
from langgraph.constants import END
from langgraph.types import Command

from vectora.agents.orchestrator import _is_post_rag, orchestrator

if TYPE_CHECKING:
    from vectora.state import State
=======
from langchain_core.runnables import RunnableConfig
from langgraph.constants import END
from langgraph.types import Command

from src.agents.orchestrator import _is_post_rag, orchestrator

if TYPE_CHECKING:
    from src.state import State

_CONFIG: RunnableConfig = {"configurable": {}}
>>>>>>> dev

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
<<<<<<< HEAD
        cmd = await orchestrator(state)
=======
        cmd = await orchestrator(state, config=_CONFIG)
>>>>>>> dev
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
<<<<<<< HEAD
        cmd = await orchestrator(state)
=======
        cmd = await orchestrator(state, config=_CONFIG)
>>>>>>> dev
        assert isinstance(cmd, Command)
        assert cmd.update is not None

        # Se o LLM entrou em fallback por rate limit, o routing é 'respond' e a
        # mensagem contém texto de erro — skip em vez de falhar
        if cmd.goto == END:
            msgs = cmd.update.get("messages", [])
            content = str(msgs[0].content).lower() if msgs else ""
            if (
                "erro interno" in content
                or "quota" in content
                or "rate limit" in content
            ):
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
<<<<<<< HEAD
        cmd = await orchestrator(state)
=======
        cmd = await orchestrator(state, config=_CONFIG)
>>>>>>> dev
        assert isinstance(cmd, Command)
        assert cmd.update is not None

        if cmd.goto == END:
            msgs = cmd.update.get("messages", [])
            content = str(msgs[0].content).lower() if msgs else ""
            if (
                "erro interno" in content
                or "quota" in content
                or "rate limit" in content
            ):
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
<<<<<<< HEAD
        cmd = await orchestrator(state)
=======
        cmd = await orchestrator(state, config=_CONFIG)
>>>>>>> dev
        assert cmd.update is not None
        assert cmd.update["routing_decision"] == "respond"

    @pytest.mark.asyncio
    async def test_empty_messages_defaults_to_respond(self):
        """Sem mensagens → fallback inline (respond)."""
        state: State = {"messages": [], "session_metadata": {}}
<<<<<<< HEAD
        cmd = await orchestrator(state)
=======
        cmd = await orchestrator(state, config=_CONFIG)
>>>>>>> dev
        assert cmd.goto == END

    @pytest.mark.asyncio
    async def test_no_human_message_defaults_to_respond(self):
        """Sem HumanMessage → fallback inline (respond)."""
        state: State = {
            "messages": [AIMessage(content="resposta")],
            "session_metadata": {},
        }
<<<<<<< HEAD
        cmd = await orchestrator(state)
=======
        cmd = await orchestrator(state, config=_CONFIG)
>>>>>>> dev
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
<<<<<<< HEAD
        cmd = await orchestrator(state)
        if cmd.goto == "coder":
=======
        cmd = await orchestrator(state, config=_CONFIG)
        if cmd.goto == "coder":
            assert cmd.update is not None
>>>>>>> dev
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
<<<<<<< HEAD
        cmd = await orchestrator(state)
        if cmd.goto == END:
=======
        cmd = await orchestrator(state, config=_CONFIG)
        if cmd.goto == END:
            assert cmd.update is not None
>>>>>>> dev
            assert cmd.update.get("orchestrator_task") is None
            messages = cmd.update.get("messages", [])
            assert len(messages) == 1


# ---------------------------------------------------------------------------
# A6.2 — regressão do loop orchestrator ↔ rag_subgraph
# ---------------------------------------------------------------------------


class TestIsPostRag:
    """_is_post_rag — detecção determinística do marcador rag_context."""

    def test_rag_context_as_last_message_detected(self):
        msgs = [
            HumanMessage(content="pergunta"),
            SystemMessage(content="## Contexto Recuperado (RAG)", name="rag_context"),
        ]
        assert _is_post_rag(msgs) is True

    def test_other_systemmessage_not_detected(self):
        msgs = [SystemMessage(content="ctx", name="project_context")]
        assert _is_post_rag(msgs) is False

    def test_human_last_not_detected(self):
        assert _is_post_rag([HumanMessage(content="pergunta")]) is False

    def test_empty_messages_not_detected(self):
        assert _is_post_rag([]) is False

    def test_rag_context_not_last_not_detected(self):
        """rag_context de turno anterior, já seguido de resposta → não é pós-RAG."""
        msgs = [
            SystemMessage(content="ctx antigo", name="rag_context"),
            AIMessage(content="resposta do turno anterior"),
            HumanMessage(content="nova pergunta"),
        ]
        assert _is_post_rag(msgs) is False


class TestOrchestratorPostRAG:
    """Caminho de síntese pós-RAG — sempre encerra em END, nunca re-roteia."""

    @pytest.mark.asyncio
    async def test_post_rag_routes_to_end_never_rag(self):
        """Última msg = rag_context → síntese → END (nunca 'rag_subgraph')."""
        state: State = {
            "messages": [
                HumanMessage(content="me responda com rag: o que é o ability system?"),
                SystemMessage(
                    content="## Contexto Recuperado (RAG)\n\nDoc relevante...",
                    name="rag_context",
                ),
            ],
            "session_metadata": {},
        }
        fake_llm = AsyncMock()
        fake_llm.ainvoke = AsyncMock(
            return_value=AIMessage(content="Resposta sintetizada do contexto.")
        )
<<<<<<< HEAD
        with patch(
            "vectora.agents.orchestrator._get_synthesis_llm", return_value=fake_llm
        ):
            cmd = await orchestrator(state)

        assert cmd.goto == END
        assert cmd.goto != "rag_subgraph"
=======
        with patch("src.agents.orchestrator._get_synthesis_llm", return_value=fake_llm):
            cmd = await orchestrator(state, config=_CONFIG)

        assert cmd.goto == END
        assert cmd.goto != "rag_subgraph"
        assert cmd.update is not None
>>>>>>> dev
        assert cmd.update["routing_decision"] == "respond"
        msgs = cmd.update.get("messages", [])
        assert len(msgs) == 1
        assert isinstance(msgs[0], AIMessage)
        assert msgs[0].content == "Resposta sintetizada do contexto."
        fake_llm.ainvoke.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_post_rag_synthesis_failure_has_fallback(self):
        """LLM de síntese falha → ainda encerra em END com fallback não-vazio."""
        state: State = {
            "messages": [
                HumanMessage(content="o que diz a base sobre X?"),
                SystemMessage(
                    content="## Contexto Recuperado (RAG)\n\nNenhum documento...",
                    name="rag_context",
                ),
            ],
            "session_metadata": {},
        }
        fake_llm = AsyncMock()
        fake_llm.ainvoke = AsyncMock(side_effect=Exception("LLM indisponível"))
<<<<<<< HEAD
        with patch(
            "vectora.agents.orchestrator._get_synthesis_llm", return_value=fake_llm
        ):
            cmd = await orchestrator(state)

        assert cmd.goto == END
=======
        with patch("src.agents.orchestrator._get_synthesis_llm", return_value=fake_llm):
            cmd = await orchestrator(state, config=_CONFIG)

        assert cmd.goto == END
        assert cmd.update is not None
>>>>>>> dev
        msgs = cmd.update.get("messages", [])
        assert len(msgs) == 1
        assert isinstance(msgs[0], AIMessage)
        assert msgs[0].content  # fallback não-vazio

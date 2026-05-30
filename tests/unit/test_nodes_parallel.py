"""Tests para C5 — Parallel Agent Execution (parallel_dispatch + orchestrator routing)."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _state(**kw) -> Any:
    base = {
        "messages": [HumanMessage(content="compare JWT vs OAuth2 e mostre código")],
        "session_metadata": {},
    }
    base.update(kw)
    return base


def _task(agent: str, query: str, reason: str = "") -> Any:
    return {"agent": agent, "task_query": query, "reason": reason}


# ---------------------------------------------------------------------------
# C5 — parallel_dispatch node
# ---------------------------------------------------------------------------


class TestParallelDispatch:
    @pytest.mark.asyncio
    async def test_empty_tasks_returns_empty_results(self):
        """Sem tasks, retorna lista vazia sem chamar o LLM."""
        from vectora.graph import parallel_dispatch

        config: Any = {"configurable": {}}
        result = await parallel_dispatch(_state(), config=config)
        assert result["parallel_results"] == []

    @pytest.mark.asyncio
    async def test_executes_all_tasks(self):
        """Todas as tasks devem ser executadas e retornar resultados."""
        from vectora.graph import parallel_dispatch

        config: Any = {"configurable": {}}
        tasks = [
            _task("search", "buscar documentação JWT"),
            _task("coder", "implementar verificação JWT em Python"),
        ]
        state = _state(parallel_tasks=tasks)

        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(
            return_value=AIMessage(content="resposta do agente")
        )

        with patch("vectora.services.utils.load_llm", return_value=mock_llm):
            result = await parallel_dispatch(state, config=config)

        assert len(result["parallel_results"]) == 2
        assert all(r["success"] for r in result["parallel_results"])

    @pytest.mark.asyncio
    async def test_results_contain_agent_and_task_fields(self):
        """Cada resultado deve conter agent, task, reason, response, success."""
        from vectora.graph import parallel_dispatch

        config: Any = {"configurable": {}}
        tasks = [_task("search", "busca JWT", "precisamos de contexto")]
        state = _state(parallel_tasks=tasks)

        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(
            return_value=AIMessage(content="resultado da busca")
        )

        with patch("vectora.services.utils.load_llm", return_value=mock_llm):
            result = await parallel_dispatch(state, config=config)

        r = result["parallel_results"][0]
        assert r["agent"] == "search"
        assert r["task"] == "busca JWT"
        assert r["reason"] == "precisamos de contexto"
        assert "resultado da busca" in r["response"]
        assert r["success"] is True

    @pytest.mark.asyncio
    async def test_task_failure_marked_as_not_success(self):
        """Uma task que falha não deve derrubar as demais — marca success=False."""
        from vectora.graph import parallel_dispatch

        config: Any = {"configurable": {}}
        tasks = [
            _task("search", "busca normal"),
            _task("coder", "código que vai falhar"),
        ]
        state = _state(parallel_tasks=tasks)

        call_count = 0

        async def fake_invoke(messages, config=None):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise RuntimeError("LLM indisponível")
            return AIMessage(content="ok")

        mock_llm = AsyncMock()
        mock_llm.ainvoke = fake_invoke

        with patch("vectora.services.utils.load_llm", return_value=mock_llm):
            result = await parallel_dispatch(state, config=config)

        results = result["parallel_results"]
        assert len(results) == 2
        successes = [r["success"] for r in results]
        assert True in successes  # ao menos 1 sucesso
        assert False in successes  # ao menos 1 falha

    @pytest.mark.asyncio
    async def test_uses_agent_specific_prompt(self):
        """Cada tipo de agente deve receber seu próprio system prompt."""
        from vectora.graph import _PARALLEL_AGENT_PROMPTS, parallel_dispatch

        config: Any = {"configurable": {}}
        tasks = [
            _task("coder", "escrever função"),
            _task("search", "pesquisar docs"),
            _task("rag", "consultar base"),
        ]
        state = _state(parallel_tasks=tasks)

        captured_messages = []

        async def capture_invoke(messages, config=None):
            captured_messages.append(messages)
            return AIMessage(content="ok")

        mock_llm = AsyncMock()
        mock_llm.ainvoke = capture_invoke

        with patch("vectora.services.utils.load_llm", return_value=mock_llm):
            await parallel_dispatch(state, config=config)

        # Verifica que cada task usou o system prompt do seu agente
        assert len(captured_messages) == 3
        system_contents = [msgs[0].content for msgs in captured_messages]
        assert _PARALLEL_AGENT_PROMPTS["coder"] in system_contents
        assert _PARALLEL_AGENT_PROMPTS["search"] in system_contents
        assert _PARALLEL_AGENT_PROMPTS["rag"] in system_contents

    @pytest.mark.asyncio
    async def test_unknown_agent_uses_search_prompt(self):
        """Agente desconhecido usa o prompt de search como fallback."""
        from vectora.graph import _PARALLEL_AGENT_PROMPTS, parallel_dispatch

        config: Any = {"configurable": {}}
        tasks = [_task("inexistente", "tarefa desconhecida")]
        state = _state(parallel_tasks=tasks)

        captured = []

        async def capture_invoke(messages, config=None):
            captured.append(messages[0].content)
            return AIMessage(content="fallback")

        mock_llm = AsyncMock()
        mock_llm.ainvoke = capture_invoke

        with patch("vectora.services.utils.load_llm", return_value=mock_llm):
            await parallel_dispatch(state, config=config)

        assert captured[0] == _PARALLEL_AGENT_PROMPTS["search"]


# ---------------------------------------------------------------------------
# C5 — estado no grafo: routing_decision e parallel_tasks
# ---------------------------------------------------------------------------


class TestParallelStateFields:
    def test_state_has_parallel_tasks_field(self):
        """State deve suportar parallel_tasks."""
        from vectora.state import State

        s: State = {
            "messages": [],
            "session_metadata": {},
            "parallel_tasks": [{"agent": "search", "task_query": "x"}],  # ty: ignore[invalid-argument-type]
        }
        assert s["parallel_tasks"] is not None
        assert s["parallel_tasks"][0]["agent"] == "search"

    def test_state_has_parallel_results_field(self):
        """State deve suportar parallel_results."""
        from vectora.state import State

        s: State = {
            "messages": [],
            "session_metadata": {},
            "parallel_results": [  # ty: ignore[invalid-argument-type]
                {"agent": "search", "response": "ok", "success": True}
            ],
        }
        assert s["parallel_results"] is not None
        assert s["parallel_results"][0]["success"] is True

    def test_routing_decision_accepts_parallel(self):
        """routing_decision deve aceitar o valor 'parallel'."""
        from vectora.state import State

        s: State = {
            "messages": [],
            "session_metadata": {},
            "routing_decision": "parallel",
        }
        assert s["routing_decision"] == "parallel"


# ---------------------------------------------------------------------------
# C5 — graph routing: parallel_dispatch é destino quando routing_decision=parallel
# ---------------------------------------------------------------------------


class TestOrchestratorParallelRouting:
    def test_parallel_maps_to_parallel_dispatch(self):
        """_orchestrator_route deve mapear 'parallel' → 'parallel_dispatch'."""
        from vectora.graph import _orchestrator_route

        state = _state(routing_decision="parallel")
        assert _orchestrator_route(state) == "parallel_dispatch"

    def test_respond_maps_to_end(self):
        """Routing 'respond' continua mapeando para END."""
        from langgraph.constants import END

        from vectora.graph import _orchestrator_route

        state = _state(routing_decision="respond")
        assert _orchestrator_route(state) == END

    def test_unknown_maps_to_end(self):
        """Routing desconhecido deve cair no END como fallback seguro."""
        from langgraph.constants import END

        from vectora.graph import _orchestrator_route

        state = _state(routing_decision="inexistente")
        assert _orchestrator_route(state) == END


# ---------------------------------------------------------------------------
# C5 — OrchestratorDecision: SubTask e action=parallel
# ---------------------------------------------------------------------------


class TestSubTaskModel:
    def test_subtask_creation(self):
        """SubTask deve aceitar agent, task_query e reason opcional."""
        from vectora.types import SubTask

        t = SubTask(agent="search", task_query="buscar JWT docs")
        assert t.agent == "search"
        assert t.task_query == "buscar JWT docs"
        assert t.reason == ""  # default

    def test_subtask_with_reason(self):
        from vectora.types import SubTask

        t = SubTask(
            agent="coder", task_query="implementar auth", reason="precisa de código"
        )
        assert t.reason == "precisa de código"

    def test_orchestrator_decision_accepts_parallel(self):
        """OrchestratorDecision deve aceitar action='parallel' com parallel_tasks."""
        from vectora.types import OrchestratorDecision, SubTask

        tasks = [
            SubTask(agent="search", task_query="busca"),
            SubTask(agent="coder", task_query="código"),
        ]
        decision = OrchestratorDecision(
            action="parallel",
            parallel_tasks=tasks,
            reason="tasks independentes identificadas",
        )
        assert decision.action == "parallel"
        assert decision.parallel_tasks is not None
        assert len(decision.parallel_tasks) == 2

    def test_orchestrator_decision_parallel_tasks_none_by_default(self):
        """parallel_tasks deve ser None por padrão (não quebra decisions normais)."""
        from vectora.types import OrchestratorDecision

        decision = OrchestratorDecision(
            action="respond", response="oi", reason="resposta inline"
        )
        assert decision.parallel_tasks is None

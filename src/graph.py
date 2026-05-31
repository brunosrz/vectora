"""LangGraph Construction — Orchestrator + Sub-agents + RAG Pipeline.

Topologia:
  START → orchestrator
            ├── [respond]   → END
            ├── [coder]     → coder → (hitl_check →) coder_tools ↻
            │                       → coder_finalize → orchestrator (síntese)
            ├── [search]    → search → search_tools → process_retrieval ↻
            │                       → search_finalize → orchestrator (síntese)
            ├── [parallel]  → parallel_dispatch → orchestrator (síntese)
            └── [rag]       → rag_expand_query → rag_retrieve → rag_decide_node
                                  ├── (score ≥ 0.7) → rag_inject
                                  ├── (score ≥ 0.4) → rag_rerank → rag_search_audit → rag_inject
                                  └── (score < 0.4) → rag_websearch → rag_search_audit → rag_inject
                                                     → orchestrator (síntese inline)

O orchestrator decide em: respond | coder | search | rag | parallel.
Os nós RAG são nós convencionais do grafo principal — sem subgrafo separado.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from langgraph.constants import END, START
from langgraph.graph.state import CompiledStateGraph, StateGraph
from langgraph.prebuilt.tool_node import tools_condition

from src.agents.coder import coder, coder_finalize
from src.agents.orchestrator import _PARALLEL_AGENT_PROMPTS, orchestrator
from src.agents.search import search, search_finalize
from src.context import Context
from src.nodes.debug import DiagnosticToolNode
from src.nodes.engine import process_retrieval
from src.nodes.hitl import hitl_check
from src.nodes.rag_subgraph import (
    _rag_decide_node,
    _route_after_decide,
    rag_expand_query,
    rag_inject,
    rag_rerank,
    rag_retrieve,
)
from src.nodes.tools import ALL_TOOLS
from src.state import State

if TYPE_CHECKING:
    from langchain_core.runnables import RunnableConfig
    from langgraph.pregel.main import BaseCheckpointSaver

    from src.types.agents import SubTask

logger = logging.getLogger(__name__)


def _hitl_route(state: State) -> str:
    """Após hitl_check: vai para coder_tools (aprovado) ou de volta ao coder (rejeitado)."""
    if state.get("hitl_cancelled"):
        return "coder"
    return "coder_tools"


def _orchestrator_route(state: State) -> str:
    """Mapeia routing_decision para o nó de destino após orchestrator."""
    decision = state.get("routing_decision") or "respond"
    mapping = {
        "respond": END,  # AIMessage já injetado pelo orchestrator
        "search": "search",
        "coder": "coder",
        "rag": "rag_expand_query",
        "parallel": "parallel_dispatch",  # C5
        "tools": "search",
    }
    return mapping.get(decision, END)


async def parallel_dispatch(state: State, config: RunnableConfig) -> dict:
    """Executa múltiplas tasks de agentes em paralelo via asyncio.gather (C5).

    Cada task �� executada chamando o LLM com o prompt do agent correspondente.
    Em modo paralelo, agentes respondem diretamente sem tool calls — é uma
    "consulta rápida" em paralelo antes da síntese pelo orchestrator.

    Após coleta, retorna ao orchestrator via edge direto para síntese final.
    """
    import asyncio

    from langchain_core.messages import HumanMessage, SystemMessage
    from langchain_core.runnables import RunnableConfig

    from src.services.utils import load_llm

    tasks = state.get("parallel_tasks") or []
    if not tasks:
        logger.info("parallel_dispatch: nenhuma task, retornando vazio")
        return {"parallel_results": []}

    async def _run_task(task: SubTask | dict) -> dict:
        # SubTask (Pydantic) e dict expõem ``.get`` graças ao mixin em SubTask.
        agent = task.get("agent", "search")
        task_query = task.get("task_query", "")
        reason = task.get("reason", "")

        system_prompt = _PARALLEL_AGENT_PROMPTS.get(
            agent, _PARALLEL_AGENT_PROMPTS["search"]
        )
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=task_query),
        ]

        try:
            llm = load_llm()
            response = await llm.ainvoke(messages, config=config)
            return {
                "agent": agent,
                "task": task_query,
                "reason": reason,
                "response": str(getattr(response, "content", response)),
                "success": True,
            }
        except Exception as e:
            logger.warning("parallel_dispatch: task[%s] falhou: %s", agent, e)
            return {
                "agent": agent,
                "task": task_query,
                "reason": reason,
                "response": f"Erro ao executar task: {e}",
                "success": False,
            }

    logger.info("parallel_dispatch: executando %d tasks em paralelo", len(tasks))
    results = await asyncio.gather(*[_run_task(t) for t in tasks])
    logger.info(
        "parallel_dispatch: %d/%d tasks bem-sucedidas",
        sum(1 for r in results if r.get("success")),
        len(results),
    )
    return {"parallel_results": list(results)}


def build_graph(
    checkpointer: BaseCheckpointSaver | None = None,
) -> CompiledStateGraph[State, Context, State, State]:  # ty: ignore[invalid-type-arguments]
    """Constrói LangGraph com orchestrator + sub-agents + RAG subgraph.

    `checkpointer` é opcional: o chat passa um AsyncSqliteSaver para persistir
    sessões. O LangGraph Studio (`langgraph dev`) chama `build_graph()` sem
    argumentos e injeta a própria camada de persistência — por isso o default
    é None. `compile(checkpointer=None)` é válido e não persiste nada.
    """
    logger.info("Building LangGraph: orchestrator + subagents + RAG pipeline")

    builder = StateGraph(  # type: ignore[type-arg,arg-type]
        state_schema=State,  # ty: ignore[invalid-argument-type]
        context_schema=Context,
        input_schema=State,  # ty: ignore[invalid-argument-type]
        output_schema=State,  # ty: ignore[invalid-argument-type]
    )

    # ToolNodes com diagnóstico
    search_tools_node = DiagnosticToolNode(tools=ALL_TOOLS)
    coder_tools_node = DiagnosticToolNode(tools=ALL_TOOLS)

    # --- Nós ---
    builder.add_node("orchestrator", orchestrator)

    builder.add_node("search", search)
    builder.add_node("search_tools", search_tools_node)
    builder.add_node("search_finalize", search_finalize)

    builder.add_node("coder", coder)
    builder.add_node("hitl_check", hitl_check)
    builder.add_node("coder_tools", coder_tools_node)
    builder.add_node("coder_finalize", coder_finalize)

    builder.add_node("process_retrieval", process_retrieval)
    builder.add_node("parallel_dispatch", parallel_dispatch)

    # Nós RAG — pipeline achatado no grafo principal
    # Score baixo → search (com rag_pending=True) → rag_inject
    # Score médio → rag_rerank → rag_inject
    # Score alto  → rag_inject direto
    builder.add_node("rag_expand_query", rag_expand_query)
    builder.add_node("rag_retrieve", rag_retrieve)
    builder.add_node("rag_decide_node", _rag_decide_node)
    builder.add_node("rag_rerank", rag_rerank)
    builder.add_node("rag_inject", rag_inject)

    # --- Edges ---

    # START → orchestrator (ponto de entrada único)
    builder.add_edge(START, "orchestrator")

    # orchestrator → destino (baseado em routing_decision)
    builder.add_conditional_edges(
        "orchestrator",
        _orchestrator_route,
        {
            END: END,
            "search": "search",
            "coder": "coder",
            "rag_expand_query": "rag_expand_query",
            "parallel_dispatch": "parallel_dispatch",
        },
    )

    # C5 — parallel_dispatch → orchestrator para síntese dos resultados paralelos
    builder.add_edge("parallel_dispatch", "orchestrator")

    # RAG pipeline achatado
    builder.add_edge("rag_expand_query", "rag_retrieve")
    builder.add_edge("rag_retrieve", "rag_decide_node")
    builder.add_conditional_edges(
        "rag_decide_node",
        _route_after_decide,
        {
            "rag_inject": "rag_inject",  # score alto → direto
            "rag_rerank": "rag_rerank",  # score médio → rerank
            "search": "search",  # score baixo → search real (rag_pending=True)
        },
    )
    builder.add_edge("rag_rerank", "rag_inject")
    builder.add_edge("rag_inject", "orchestrator")

    # search → search_tools → process_retrieval → search (loop)
    # ao terminar → search_finalize → orchestrator (síntese estruturada)
    builder.add_conditional_edges(
        "search",
        lambda s: (
            "search_tools" if tools_condition(s) == "tools" else "search_finalize"
        ),
        {"search_tools": "search_tools", "search_finalize": "search_finalize"},
    )
    builder.add_edge("search_tools", "process_retrieval")
    builder.add_edge("process_retrieval", "search")
    # search_finalize → orchestrator (caminho normal)
    #                 → rag_inject   (quando rag_pending=True — search foi invocado pelo RAG)
    builder.add_conditional_edges(
        "search_finalize",
        lambda s: "rag_inject" if s.get("rag_pending") else "orchestrator",
        {"rag_inject": "rag_inject", "orchestrator": "orchestrator"},
    )

    # coder: tem tool_calls → hitl_check (HITL gate) → coder_tools → coder
    # Sem tool_calls → coder_finalize → orchestrator (síntese estruturada)
    builder.add_conditional_edges(
        "coder",
        lambda s: "hitl_check" if tools_condition(s) == "tools" else "coder_finalize",
        {"hitl_check": "hitl_check", "coder_finalize": "coder_finalize"},
    )
    # hitl_check: aprovado → coder_tools; rejeitado (cancel msgs) → coder
    builder.add_conditional_edges(
        "hitl_check",
        _hitl_route,
        {"coder_tools": "coder_tools", "coder": "coder"},
    )
    builder.add_edge("coder_tools", "coder")
    builder.add_edge("coder_finalize", "orchestrator")

    compiled = builder.compile(checkpointer=checkpointer)
    logger.info(
        "Graph compiled: orchestrator + search/coder agents + RAG pipeline (flat)"
    )
    return compiled  # type: ignore[return-value]  # ty: ignore[invalid-return-type]

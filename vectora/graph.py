"""LangGraph Construction — Orchestrator + Sub-agents + RAG Subgraph.

Topologia:
  START → orchestrator
            ├── [respond]       → END
            ├── [coder]         → coder → coder_tools ↻ → END
            ├── [search]        → search → search_tools → process_retrieval ↻ → END
            └── [rag_subgraph]  → rag_subgraph → orchestrator (síntese inline)

O orchestrator decide em: respond (inline) | coder | search | rag.
Quando delega, injeta orchestrator_task no state para o sub-agent executar
com instrução clara, sem depender de inferência do histórico bruto.
Após o rag_subgraph injetar contexto em messages, o orchestrator é acionado
novamente para sintetizar a resposta diretamente — sem nó direct separado.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from langgraph.constants import END, START
from langgraph.graph.state import CompiledStateGraph, StateGraph
from langgraph.prebuilt.tool_node import tools_condition

from vectora.agents.coder import coder
from vectora.agents.orchestrator import orchestrator
from vectora.agents.search import search
from vectora.context import Context
from vectora.nodes.debug import DiagnosticToolNode
from vectora.nodes.engine import process_retrieval
from vectora.nodes.rag_subgraph import build_rag_subgraph
from vectora.nodes.tools import ALL_TOOLS
from vectora.state import State

if TYPE_CHECKING:
    from langgraph.pregel.main import BaseCheckpointSaver

logger = logging.getLogger(__name__)


def _orchestrator_route(state: State) -> str:
    """Mapeia routing_decision para o nó de destino após orchestrator."""
    decision = state.get("routing_decision") or "respond"
    mapping = {
        "respond": END,  # AIMessage já injetado pelo orchestrator
        "search": "search",
        "coder": "coder",
        "rag": "rag_subgraph",
        "tools": "search",
    }
    return mapping.get(decision, END)


def build_graph(
    checkpointer: BaseCheckpointSaver,
) -> CompiledStateGraph[State, Context, State, State]:  # ty: ignore[invalid-type-arguments]
    """Constrói LangGraph com orchestrator + sub-agents + RAG subgraph."""
    logger.info("Building LangGraph: orchestrator + subagents topology")

    builder = StateGraph(  # type: ignore[type-arg,arg-type]
        state_schema=State,  # ty: ignore[invalid-argument-type]
        context_schema=Context,
        input_schema=State,  # ty: ignore[invalid-argument-type]
        output_schema=State,  # ty: ignore[invalid-argument-type]
    )

    # Subgrafo RAG compilado como nó atômico
    rag_subgraph = build_rag_subgraph()

    # ToolNodes com diagnóstico
    search_tools_node = DiagnosticToolNode(tools=ALL_TOOLS)
    coder_tools_node = DiagnosticToolNode(tools=ALL_TOOLS)

    # --- Nós ---
    builder.add_node("orchestrator", orchestrator)
    builder.add_node("rag_subgraph", rag_subgraph)

    builder.add_node("search", search)
    builder.add_node("search_tools", search_tools_node)

    builder.add_node("coder", coder)
    builder.add_node("coder_tools", coder_tools_node)

    builder.add_node("process_retrieval", process_retrieval)

    # --- Edges ---

    # START → orchestrator (ponto de entrada único)
    builder.add_edge(START, "orchestrator")

    # orchestrator → destino (baseado em routing_decision)
    builder.add_conditional_edges(
        "orchestrator",
        _orchestrator_route,
        {
            END: END,  # respond inline
            "search": "search",
            "coder": "coder",
            "rag_subgraph": "rag_subgraph",
        },
    )

    # RAG subgraph → orchestrator para síntese inline (sem direct)
    builder.add_edge("rag_subgraph", "orchestrator")

    # search → search_tools → process_retrieval → search (loop)
    # ao terminar → END
    builder.add_conditional_edges(
        "search",
        lambda s: "search_tools" if tools_condition(s) == "tools" else END,
        {"search_tools": "search_tools", END: END},
    )
    builder.add_edge("search_tools", "process_retrieval")
    builder.add_edge("process_retrieval", "search")

    # coder: loop de tools → ao terminar → END
    builder.add_conditional_edges(
        "coder",
        lambda s: "coder_tools" if tools_condition(s) == "tools" else END,
        {"coder_tools": "coder_tools", END: END},
    )
    builder.add_edge("coder_tools", "coder")

    compiled = builder.compile(checkpointer=checkpointer)
    logger.info("Graph compiled: orchestrator + search/coder agents + RAG subgraph")
    return compiled  # type: ignore[return-value]  # ty: ignore[invalid-return-type]

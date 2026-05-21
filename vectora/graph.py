"""LangGraph Construction — Supervisor + Subagents + RAG Subgraph.

Topologia:
  START → supervisor
            ├── direct_worker  → (memory tools) → END
            ├── search_worker  → (search tools) → process_retrieval → supervisor
            ├── coder_worker   → (fs tools)     → supervisor
            └── rag_subgraph   → direct_worker  → END

O supervisor classifica a intenção em: direct | search | coder | rag.
Após cada worker terminar, o supervisor pode re-rotear (ex: search completou
busca → vai para direct para sintetizar a resposta final).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from langgraph.constants import END, START
from langgraph.graph.state import CompiledStateGraph, StateGraph
from langgraph.prebuilt.tool_node import tools_condition

from vectora.agents.coder import coder
from vectora.agents.direct import direct
from vectora.agents.search import search
from vectora.agents.supervisor import supervisor
from vectora.context import Context
from vectora.nodes.debug import DiagnosticToolNode
from vectora.nodes.engine import process_retrieval
from vectora.nodes.rag_subgraph import build_rag_subgraph
from vectora.nodes.tools import ALL_TOOLS, MEMORY_TOOLS
from vectora.state import State

if TYPE_CHECKING:
    from langgraph.pregel.main import BaseCheckpointSaver

logger = logging.getLogger(__name__)


def _supervisor_route(state: State) -> str:
    """Mapeia routing_decision para o nó de destino."""
    decision = state.get("routing_decision") or "direct"
    mapping = {
        "direct": "direct",
        "search": "search",
        "coder": "coder",
        "rag": "rag_subgraph",
        "tools": "search",
    }
    return mapping.get(decision, "direct")


def build_graph(
    checkpointer: BaseCheckpointSaver,
) -> CompiledStateGraph[State, Context, State, State]:  # ty: ignore[invalid-type-arguments]
    """Constrói LangGraph com supervisor + workers especializados + RAG subgraph."""
    logger.info("Building LangGraph: supervisor + subagents topology")

    builder = StateGraph(  # type: ignore[type-arg,arg-type]  # langgraph stubs don't model context_schema generics
        state_schema=State,  # ty: ignore[invalid-argument-type]
        context_schema=Context,
        input_schema=State,  # ty: ignore[invalid-argument-type]
        output_schema=State,  # ty: ignore[invalid-argument-type]
    )

    # Subgrafo RAG compilado como nó atômico
    rag_subgraph = build_rag_subgraph()

    # ToolNodes com diagnóstico — todos usam ALL_TOOLS
    # A diferença entre agentes é o system prompt, não as ferramentas disponíveis
    search_tools_node = DiagnosticToolNode(tools=ALL_TOOLS)
    coder_tools_node = DiagnosticToolNode(tools=ALL_TOOLS)
    direct_tools_node = DiagnosticToolNode(tools=ALL_TOOLS)

    # --- Nós ---
    builder.add_node("supervisor", supervisor)
    builder.add_node("rag_subgraph", rag_subgraph)

    builder.add_node("direct", direct)
    builder.add_node("direct_tools", direct_tools_node)

    builder.add_node("search", search)
    builder.add_node("search_tools", search_tools_node)

    builder.add_node("coder", coder)
    builder.add_node("coder_tools", coder_tools_node)

    builder.add_node("process_retrieval", process_retrieval)

    # --- Edges ---

    # START → supervisor (ponto de entrada único)
    builder.add_edge(START, "supervisor")

    # supervisor → agents (baseado em routing_decision)
    builder.add_conditional_edges(
        "supervisor",
        _supervisor_route,
        {
            "direct": "direct",
            "search": "search",
            "coder": "coder",
            "rag_subgraph": "rag_subgraph",
        },
    )

    # RAG subgraph → direct para síntese final
    builder.add_edge("rag_subgraph", "direct")

    # direct → memory tools se precisar, senão END
    builder.add_conditional_edges(
        "direct",
        tools_condition,
        {"tools": "direct_tools", END: END},
    )
    builder.add_edge("direct_tools", "direct")

    # search → search_tools → process_retrieval (cascading web→LanceDB) → search
    builder.add_conditional_edges(
        "search",
        tools_condition,
        {"tools": "search_tools", END: END},
    )
    builder.add_edge("search_tools", "process_retrieval")
    builder.add_edge("process_retrieval", "search")

    # coder → coder_tools → coder (loop até concluir)
    builder.add_conditional_edges(
        "coder",
        tools_condition,
        {"tools": "coder_tools", END: END},
    )
    builder.add_edge("coder_tools", "coder")

    compiled = builder.compile(checkpointer=checkpointer)
    logger.info(
        "Graph compiled: supervisor + direct/search/coder agents + RAG subgraph"
    )
    return compiled  # type: ignore[return-value]  # ty: ignore[invalid-return-type]  # CompiledStateGraph generic params not yet modelled by stubs

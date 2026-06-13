"""Fábrica do agente por usuário.

Centraliza o ciclo de vida do grafo LangGraph + checkpointer SQLite.
Este módulo é a fonte de verdade para:
  - Constantes HITL (``REQUIRE_APPROVAL``, ``ACCEPT_EDITS_AUTO``)
  - Mapeamento ``permission_mode → interrupt_on`` (``get_interrupt_on``)
  - Nó ``hitl_check`` do grafo
  - Builder do grafo (``build_graph``)
  - Singleton de agente por servidor (``get_user_agent``)

Cache:
    O grafo LangGraph é compilado uma vez e compartilhado entre todos os
    usuários. A consciência por usuário fica dentro dos nós:

      - ``DiagnosticToolNode`` resolve ``resolve_tools(user_id)`` a cada
        invocação, respeitando ``tool_policy`` (ABAC) + plugins MCP do user.
      - Subagents (coder/search) usam ``get_user_bound_llm`` com cache
        local ``(user_id, llm_version, tools_signature)``.

    ``_version_tracker`` armazena ``(tools_version, policy_version,
    skills_version)`` por usuário. Quando qualquer um muda entre
    requests, ``_invalidate_llm_cache(user_id)`` purga entradas stale do
    ``llm_tools._bound_cache``; o próximo request paga apenas o rebind
    (barato), sem recompilar o grafo.

    Multi-tenancy mora nos nós, não em instâncias separadas do grafo:
    ``StateGraph.compile()`` tem custo dominante e singleton-friendly,
    enquanto rebind de tools/LLM por user é barato.

Lifecycle:
    Servidor: ``awarm()`` no startup, ``aclose()`` no shutdown.
    Testes: use fixtures que chamam ``aclose()`` no teardown.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from langchain_core.messages import ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.types import interrupt

from backend.services import tool_policy
from backend.services.plugins import tools_version
from backend.services.skills import skills_version
from backend.state import State

if TYPE_CHECKING:
    from langgraph.checkpoint.base import BaseCheckpointSaver
    from langgraph.graph.state import CompiledStateGraph

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# HITL configuration constants (permanent home)
# ---------------------------------------------------------------------------

#: Tools destrutivas que pausam o grafo para aprovação do usuário.
REQUIRE_APPROVAL: frozenset[str] = frozenset(
    {"terminal", "terminal_tool", "file_write", "file_write_tool"}
)

#: Tools auto-aprovadas no modo "accept_edits".
ACCEPT_EDITS_AUTO: frozenset[str] = frozenset({"file_write", "file_write_tool"})


def get_interrupt_on(permission_mode: str) -> dict[str, bool]:
    """Mapeia ``permission_mode`` para o config ``interrupt_on`` do agente."""
    match permission_mode:
        case "bypass" | "auto":
            return {}
        case "accept_edits":
            return dict.fromkeys(REQUIRE_APPROVAL - ACCEPT_EDITS_AUTO, True)
        case _:  # "ask", "plan", ou desconhecido
            return dict.fromkeys(REQUIRE_APPROVAL, True)


# ---------------------------------------------------------------------------
# hitl_check — nó HITL do grafo
# ---------------------------------------------------------------------------


def _permission_mode(config: RunnableConfig | None) -> str:
    """Lê o modo de permissão do RunnableConfig (default: 'ask')."""
    if not isinstance(config, dict):
        return "ask"
    configurable = config.get("configurable")
    if not isinstance(configurable, dict):
        return "ask"
    return str(configurable.get("permission_mode") or "ask").lower()


def _resolve_pre_interrupt(
    mode: str, sensitive: list[dict[str, Any]]
) -> dict[str, Any] | list[dict[str, Any]]:
    """Resolve modos sem confirmação interativa.

    Retorna ``dict`` quando a decisão é final (auto-aprovado, plan, accept_edits
    sem nada para confirmar); retorna ``list[dict]`` com os tool_calls que
    ainda precisam de aprovação humana via ``interrupt()``.
    """
    if mode in ("auto", "bypass"):
        logger.info("HITL: modo '%s' — auto-aprovando %d tool(s)", mode, len(sensitive))
        return {"hitl_cancelled": False}

    if mode == "plan":
        logger.info(
            "HITL: modo planejamento — cancelando %d ação(ões) destrutiva(s)",
            len(sensitive),
        )
        cancel_msgs = [
            ToolMessage(
                content="Modo de planejamento ativo: ação não executada. "
                "Descreva o plano e aguarde aprovação para sair do modo.",
                tool_call_id=tc["id"],
            )
            for tc in sensitive
        ]
        return {"messages": cancel_msgs, "hitl_cancelled": True}

    if mode == "accept_edits":
        to_confirm = [
            tc for tc in sensitive if tc.get("name", "") not in ACCEPT_EDITS_AUTO
        ]
        if not to_confirm:
            logger.info("HITL: modo accept_edits — escrita de arquivos auto-aprovada")
            return {"hitl_cancelled": False}
        return to_confirm

    return sensitive


def _apply_hitl_edit(
    state: State, target_id: str, new_args: dict[str, Any] | None
) -> dict[str, Any]:
    """Aplica edição HITL ao último tool_call do user; falha → segue com args originais."""
    import copy

    from langchain_core.messages import AIMessage

    logger.info("HITL: args editados pelo usuário: %s", new_args)
    try:
        last_msg = state["messages"][-1]
        new_tool_calls = copy.deepcopy(list(getattr(last_msg, "tool_calls", []) or []))
        for tc in new_tool_calls:
            if tc.get("id") == target_id:
                tc["args"] = new_args or {}
                break
        updated_msg = AIMessage(
            content=getattr(last_msg, "content", ""),
            id=getattr(last_msg, "id", None),
            tool_calls=new_tool_calls,
        )
        return {"messages": [updated_msg], "hitl_cancelled": False}
    except Exception as exc:
        logger.warning(
            "HITL: falha ao aplicar edit, aprovando com args originais: %s", exc
        )
        return {"hitl_cancelled": False}


async def hitl_check(
    state: State,
    config: RunnableConfig = None,  # type: ignore[assignment]  # ty: ignore[invalid-parameter-default]
) -> dict[str, Any]:
    """Inspeciona tool_calls pendentes e pede confirmação quando necessário.

    Inserido entre `coder` e `coder_tools` no grafo principal.

    O comportamento depende do modo de permissão (configurable.permission_mode):
    - ask (default): pausa via interrupt() em toda tool destrutiva.
    - accept_edits: auto-aprova escrita de arquivos; ainda confirma terminal.
    - plan: não executa ações destrutivas — injeta ToolMessages de cancelamento.
    - auto / bypass: auto-aprova tudo sem pausar.
    """
    last_msg = state["messages"][-1]
    tool_calls: list[dict[str, Any]] = getattr(last_msg, "tool_calls", None) or []

    sensitive = [tc for tc in tool_calls if tc.get("name", "") in REQUIRE_APPROVAL]

    if not sensitive:
        return {"hitl_cancelled": False}

    resolved = _resolve_pre_interrupt(_permission_mode(config), sensitive)
    if isinstance(resolved, dict):
        return resolved
    to_confirm = resolved

    logger.info(
        "HITL: aguardando aprovação para %d tool(s): %s",
        len(to_confirm),
        [tc["name"] for tc in to_confirm],
    )

    payload: list[dict[str, Any]] = [
        {
            "id": tc["id"],
            "name": tc["name"],
            "args": tc.get("args", {}),
        }
        for tc in to_confirm
    ]

    decision: Any = interrupt(payload)

    if isinstance(decision, str):
        action = decision.lower()
    elif isinstance(decision, dict):
        action = str(decision.get("action", "approve")).lower()
    else:
        action = "approve"

    if action in ("approve", "yes", "sim", "s", "y", ""):
        logger.info("HITL: ações aprovadas pelo usuário")
        return {"hitl_cancelled": False}

    if action == "edit":
        new_args = decision.get("args") if isinstance(decision, dict) else {}
        return _apply_hitl_edit(state, to_confirm[0]["id"], new_args)

    logger.info("HITL: ações rejeitadas pelo usuário")
    cancel_msgs_list: list[ToolMessage] = [
        ToolMessage(
            content="Ação cancelada pelo usuário.",
            tool_call_id=tc["id"],
        )
        for tc in to_confirm
    ]
    return {"messages": cancel_msgs_list, "hitl_cancelled": True}


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------


def _hitl_route(state: State) -> str:
    """Após hitl_check: vai para coder_tools (aprovado) ou de volta ao coder (rejeitado)."""
    if state.get("hitl_cancelled"):
        return "coder"
    return "coder_tools"


def build_graph(
    checkpointer: BaseCheckpointSaver | None = None,
) -> CompiledStateGraph:
    """Constrói LangGraph com orchestrator + sub-agents + RAG pipeline.

    Topologia:
      START → orchestrator
                ├── [respond]   → END
                ├── [coder]     → coder → (hitl_check →) coder_tools ↻
                │                       → coder_finalize → orchestrator
                ├── [search]    → search → search_tools → process_retrieval ↻
                │                       → search_finalize → orchestrator
                ├── [parallel]  → parallel_dispatch → orchestrator
                └── [rag]       → rag_expand_query → rag_retrieve → rag_decide_node
                                      ├── → rag_inject
                                      ├── → rag_rerank → rag_inject
                                      └── → search (rag_pending=True) → rag_inject

    checkpointer é opcional: o chat passa AsyncSqliteSaver para persistência.
    None = sem persistência (útil em testes e LangGraph Studio).
    """
    from langgraph.constants import END, START
    from langgraph.graph.state import StateGraph
    from langgraph.prebuilt.tool_node import tools_condition

    from backend.agents.coder import coder, coder_finalize
    from backend.agents.orchestrator import _orchestrator_route, orchestrator
    from backend.agents.search import search, search_finalize
    from backend.context import Context
    from backend.nodes.debug import DiagnosticToolNode
    from backend.nodes.engine import process_retrieval
    from backend.nodes.parallel import parallel_dispatch
    from backend.nodes.rag_subgraph import (
        _rag_decide_node,
        _route_after_decide,
        rag_expand_query,
        rag_inject,
        rag_rerank,
        rag_retrieve,
    )
    from backend.nodes.tools import ALL_TOOLS

    logger.info("Building LangGraph: orchestrator + subagents + RAG pipeline")

    builder = StateGraph(  # type: ignore[type-arg,arg-type]
        state_schema=State,  # ty: ignore[invalid-argument-type]
        context_schema=Context,
        input_schema=State,  # ty: ignore[invalid-argument-type]
        output_schema=State,  # ty: ignore[invalid-argument-type]
    )

    search_tools_node = DiagnosticToolNode(tools=ALL_TOOLS)
    coder_tools_node = DiagnosticToolNode(tools=ALL_TOOLS)

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

    builder.add_node("rag_expand_query", rag_expand_query)
    builder.add_node("rag_retrieve", rag_retrieve)
    builder.add_node("rag_decide_node", _rag_decide_node)
    builder.add_node("rag_rerank", rag_rerank)
    builder.add_node("rag_inject", rag_inject)

    builder.add_edge(START, "orchestrator")

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

    builder.add_edge("parallel_dispatch", "orchestrator")

    builder.add_edge("rag_expand_query", "rag_retrieve")
    builder.add_edge("rag_retrieve", "rag_decide_node")
    builder.add_conditional_edges(
        "rag_decide_node",
        _route_after_decide,
        {
            "rag_inject": "rag_inject",
            "rag_rerank": "rag_rerank",
            "search": "search",
        },
    )
    builder.add_edge("rag_rerank", "rag_inject")
    builder.add_edge("rag_inject", "orchestrator")

    builder.add_conditional_edges(
        "search",
        lambda s: (
            "search_tools" if tools_condition(s) == "tools" else "search_finalize"
        ),
        {"search_tools": "search_tools", "search_finalize": "search_finalize"},
    )
    builder.add_edge("search_tools", "process_retrieval")
    builder.add_edge("process_retrieval", "search")
    builder.add_conditional_edges(
        "search_finalize",
        lambda s: "rag_inject" if s.get("rag_pending") else "orchestrator",
        {"rag_inject": "rag_inject", "orchestrator": "orchestrator"},
    )

    builder.add_conditional_edges(
        "coder",
        lambda s: "hitl_check" if tools_condition(s) == "tools" else "coder_finalize",
        {"hitl_check": "hitl_check", "coder_finalize": "coder_finalize"},
    )
    builder.add_conditional_edges(
        "hitl_check",
        _hitl_route,
        {"coder_tools": "coder_tools", "coder": "coder"},
    )
    builder.add_edge("coder_tools", "coder")
    builder.add_edge("coder_finalize", "orchestrator")

    compiled = builder.compile(checkpointer=checkpointer)
    logger.info("Graph compiled: orchestrator + search/coder + RAG pipeline")
    return compiled  # type: ignore[return-value]  # ty: ignore[invalid-return-type]


# ---------------------------------------------------------------------------
# Singleton de agente (lifecycle do servidor)
# ---------------------------------------------------------------------------

_graph: Any = None
_checkpointer_ctx: Any = None
_lock = asyncio.Lock()

# Rastreia (tools_version, policy_version, skills_version) vistas por usuário.
_version_tracker: dict[str, tuple[int, int, int]] = {}


async def _build_graph_async() -> Any:
    """Compila o grafo LangGraph e abre o checkpointer SQLite (chamado uma vez)."""
    global _graph, _checkpointer_ctx

    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

    db_path = str(Path.home() / ".vectora" / "checkpoints.db")
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    _checkpointer_ctx = AsyncSqliteSaver.from_conn_string(db_path)
    checkpointer = await _checkpointer_ctx.__aenter__()
    _graph = build_graph(checkpointer=checkpointer)
    logger.info("graph: grafo compilado (db=%s)", db_path)
    return _graph


async def get_user_agent(user_id: str | None = None) -> Any:
    """Retorna o grafo compilado (singleton compartilhado entre usuários).

    Garante inicialização thread-safe via asyncio.Lock. Registra a versão
    atual de tools/policy do usuário para detectar necessidade de rebind.
    """
    if _graph is None:
        async with _lock:
            if _graph is None:
                await _build_graph_async()

    if user_id:
        _track_versions(user_id)

    return _graph


def _track_versions(user_id: str) -> None:
    """Atualiza o rastreamento de versão sem bloquear o caller.

    Trinca de versões rastreada por user:
      - ``tools_version``: incrementa quando o user adiciona/remove MCP server
      - ``policy_version``: incrementa quando ``tool_policy`` muda
      - ``skills_version``: incrementa quando o user instala/remove skill
    """
    try:
        tv = tools_version(user_id)
        pv = tool_policy.policy_version(user_id)
        sv = skills_version(user_id)
        prev = _version_tracker.get(user_id)
        if prev != (tv, pv, sv):
            _version_tracker[user_id] = (tv, pv, sv)
            if prev is not None:
                _invalidate_llm_cache(user_id)
    except Exception:
        pass


def _invalidate_llm_cache(user_id: str) -> None:
    """Remove entradas stale do cache de LLM bound (llm_tools._bound_cache)."""
    try:
        from backend.services import llm_tools

        stale_keys = [k for k in llm_tools._bound_cache if k[0] == user_id]
        for k in stale_keys:
            del llm_tools._bound_cache[k]
        if stale_keys:
            logger.debug(
                "graph: %d entradas de LLM cache invalidadas para %s",
                len(stale_keys),
                user_id,
            )
    except Exception:
        pass


async def aclose() -> None:
    """Fecha o grafo + checkpointer SQLite. Idempotente.

    Deve ser chamado no shutdown do FastAPI (lifespan).
    """
    global _graph, _checkpointer_ctx

    async with _lock:
        if _checkpointer_ctx is None:
            return
        ctx = _checkpointer_ctx
        _checkpointer_ctx = None
        _graph = None
        _version_tracker.clear()
        try:
            await ctx.__aexit__(None, None, None)
            logger.info("graph: checkpointer fechado")
        except Exception as exc:
            logger.warning("graph: erro ao fechar checkpointer: %s", exc)


async def awarm() -> None:
    """Inicializa o grafo eagerly no startup (opt-in).

    Evita que a primeira request pague o custo de compilação (~3-5s).
    Falhas aqui não derrubam o servidor — apenas logam aviso.
    """
    try:
        await get_user_agent()
    except Exception as exc:
        logger.warning("graph: warmup falhou (continuando): %s", exc)

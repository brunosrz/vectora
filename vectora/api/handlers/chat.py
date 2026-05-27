"""Handler do serviço ChatService — streaming via SSE.

Endpoints:
    POST /vectora.chat.v1.ChatService/StreamChat
    POST /vectora.chat.v1.ChatService/ResumeChat
    GET  /vectora.chat.v1.ChatService/GetTools

Formato de resposta:
    Content-Type: text/event-stream
    Linhas: ``data: {"type": "<evento>", ...}\\n\\n``
    Último evento: ``data: {"type": "done", "thread_id": "...", "run_id": ""}\\n\\n``
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from vectora.api.adapters import adapt_stream
from vectora.api.schemas import (
    ErrorEvent,
    GetToolsResponse,
    ResumeChatRequest,
    StreamChatRequest,
    ToolSchema,
    encode_event,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Lazy graph loader
# ---------------------------------------------------------------------------

_graph: Any = None
_checkpointer_ctx: Any = None  # mantém o AsyncSqliteSaver vivo durante todo o processo
_graph_lock = asyncio.Lock()


async def _get_graph() -> Any:
    """Obtém o grafo LangGraph compilado (singleton).

    O ``AsyncSqliteSaver`` é um async context manager — abrimos uma vez na primeira
    chamada e mantemos a referência no módulo. O processo lifecycle cuida do
    fechamento na finalização do servidor.
    """
    global _graph, _checkpointer_ctx
    if _graph is not None:
        return _graph
    async with _graph_lock:
        if _graph is not None:  # double-check após o lock
            return _graph
        from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

        from vectora.graph import build_graph

        db_path = str(Path.home() / ".vectora" / "checkpoints.db")
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        _checkpointer_ctx = AsyncSqliteSaver.from_conn_string(db_path)
        checkpointer = await _checkpointer_ctx.__aenter__()
        _graph = build_graph(checkpointer)
        logger.info("api/chat: grafo LangGraph inicializado (db=%s)", db_path)
    return _graph


# ---------------------------------------------------------------------------
# StreamChat
# ---------------------------------------------------------------------------


@router.post("/vectora.chat.v1.ChatService/StreamChat")
async def stream_chat(request: StreamChatRequest) -> StreamingResponse:
    """Inicia ou continua uma conversa — retorna SSE stream.

    Se `thread_id` estiver vazio, cria uma nova thread e emite o ThreadEvent
    como primeiro pacote do stream. O cliente deve armazenar o thread_id
    recebido para continuar a conversa.
    """
    thread_id = request.thread_id or str(uuid.uuid4())

    try:
        graph = await _get_graph()
    except Exception as exc:
        logger.exception("api/chat: erro ao inicializar grafo")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    from langchain_core.messages import HumanMessage

    config: dict[str, Any] = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": request.config.recursion_limit or 50,
    }

    # Sobrescreve modelo/provider se fornecido na request
    if request.config.llm_provider:
        config["configurable"]["active_provider"] = request.config.llm_provider
    if request.config.model:
        config["configurable"]["active_model"] = request.config.model

    events = graph.astream_events(
        {"messages": [HumanMessage(content=request.content)]},
        config=config,
        version="v2",
    )

    return StreamingResponse(
        adapt_stream(events, thread_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Nginx: desabilita buffering de SSE
        },
    )


# ---------------------------------------------------------------------------
# ResumeChat (HITL)
# ---------------------------------------------------------------------------


@router.post("/vectora.chat.v1.ChatService/ResumeChat")
async def resume_chat(request: ResumeChatRequest) -> StreamingResponse:
    """Retoma uma execução pausada por HITL.

    `decision` pode ser:
    - ``"approve"`` — executa a tool com os args originais
    - ``"reject"`` — cancela; o agente recebe feedback de rejeição
    - ``"edit:<args_json>"`` — executa com args modificados
    """
    from langgraph.types import Command

    try:
        graph = await _get_graph()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    config: dict[str, Any] = {
        "configurable": {"thread_id": request.thread_id},
        "recursion_limit": 50,
    }

    # Monta o Command de resume
    if request.decision == "approve":
        resume_value = {"action": "approve"}
    elif request.decision == "reject":
        resume_value = {"action": "reject"}
    elif request.decision.startswith("edit:"):
        try:
            edited_args = json.loads(request.decision[5:])
            resume_value = {"action": "edit", "args": edited_args}
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=400, detail=f"Invalid edit args: {exc}"
            ) from exc
    else:
        raise HTTPException(
            status_code=400, detail=f"Unknown decision: {request.decision!r}"
        )

    events = graph.astream_events(
        Command(resume=resume_value),
        config=config,
        version="v2",
    )

    return StreamingResponse(
        adapt_stream(events, request.thread_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---------------------------------------------------------------------------
# GetTools
# ---------------------------------------------------------------------------


@router.get("/vectora.chat.v1.ChatService/GetTools")
async def get_tools() -> GetToolsResponse:
    """Retorna o schema das ferramentas disponíveis para autodescoberta da UI."""
    try:
        from vectora.nodes.tools import ALL_TOOLS
    except Exception as exc:
        logger.warning("api/chat: não foi possível carregar ALL_TOOLS: %s", exc)
        return GetToolsResponse(tools=[])

    tools: list[ToolSchema] = []
    for t in ALL_TOOLS:
        meta = getattr(t, "extras", None) or getattr(t, "metadata", None) or {}
        render_hint = meta.get("render_hint", "json")

        args_schema = "{}"
        if hasattr(t, "args_schema") and t.args_schema:
            try:
                args_schema = json.dumps(t.args_schema.model_json_schema())
            except Exception:
                pass

        tools.append(
            ToolSchema(
                name=t.name,
                description=t.description or "",
                render_hint=render_hint,
                category=meta.get("category", "general"),
                destructive=bool(meta.get("destructive", False)),
                icon=meta.get("icon", "tool"),
                args_schema_json=args_schema,
            )
        )

    return GetToolsResponse(tools=tools)

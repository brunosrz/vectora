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
import base64
import json
import logging
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from vectora.api.adapters import adapt_stream
from vectora.api.schemas import (
    Attachment,
    AttachmentKind,
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
# F1 — Helpers de attachments multimodais
# ---------------------------------------------------------------------------

#: Mapa extensão → linguagem para injeção em blocos de código
_EXT_TO_LANG: dict[str, str] = {
    "py": "python",
    "js": "javascript",
    "jsx": "javascript",
    "ts": "typescript",
    "tsx": "typescript",
    "json": "json",
    "md": "markdown",
    "sh": "bash",
    "bash": "bash",
    "zsh": "bash",
    "html": "html",
    "css": "css",
    "scss": "css",
    "sql": "sql",
    "yaml": "yaml",
    "yml": "yaml",
    "toml": "toml",
    "rs": "rust",
    "go": "go",
    "java": "java",
    "c": "c",
    "cpp": "cpp",
    "h": "c",
    "rb": "ruby",
    "php": "php",
    "swift": "swift",
    "kt": "kotlin",
    "scala": "scala",
    "r": "r",
    "tf": "hcl",
    "xml": "xml",
}


def _mime_to_lang(mime_type: str, filename: str) -> str:
    """Detecta a linguagem de programação pela extensão do arquivo.

    Retorna string vazia se não reconhecido (ex: PDF, binários).
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return _EXT_TO_LANG.get(ext, "")


def _build_human_message(content: str, attachments: list[Attachment]) -> Any:
    """Constrói HumanMessage com suporte a conteúdo multimodal.

    - Sem attachments → ``HumanMessage(content=str)`` simples
    - Imagem → content list com ``type=image_url`` (formato OpenAI)
    - Código/PDF/texto → injetado como bloco de código ou texto no content list

    O formato de ``content`` como lista é compatível com a maioria dos provedores
    multimodais (OpenAI, Anthropic, Google Gemini via LangChain).
    """
    from langchain_core.messages import HumanMessage

    if not attachments:
        return HumanMessage(content=content)

    parts: list[dict[str, Any]] = [{"type": "text", "text": content}]

    for att in attachments:
        if att.kind == AttachmentKind.IMAGE:
            parts.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{att.mime_type};base64,{att.base64_data}"
                    },
                }
            )
        else:
            # Código, PDF ou texto — decodifica e injeta como texto
            try:
                decoded = base64.b64decode(att.base64_data).decode(
                    "utf-8", errors="replace"
                )
            except Exception:
                decoded = "[conteúdo não pôde ser decodificado]"

            lang = _mime_to_lang(att.mime_type, att.name)
            if lang:
                block = f"\n[Arquivo: {att.name}]\n```{lang}\n{decoded}\n```"
            else:
                block = f"\n[Arquivo: {att.name}]\n{decoded}"

            parts.append({"type": "text", "text": block})

    return HumanMessage(content=parts)


# ---------------------------------------------------------------------------
# Lazy graph loader
# ---------------------------------------------------------------------------

_graph: Any = None
_checkpointer_ctx: Any = None  # mantém o AsyncSqliteSaver vivo durante todo o processo
_graph_lock = asyncio.Lock()


async def _get_graph() -> Any:
    """Obtém o grafo LangGraph compilado (singleton).

    O ``AsyncSqliteSaver`` é um async context manager — abrimos uma vez na primeira
    chamada e mantemos a referência no módulo. ``aclose_graph()`` fecha tudo no
    shutdown do servidor.
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


async def aclose_graph() -> None:
    """Fecha o grafo + checkpointer SQLite. Idempotente.

    Deve ser chamado no shutdown do FastAPI (lifespan). Encapsula o estado
    privado do módulo (``_graph``, ``_checkpointer_ctx``) — o resto da app
    nunca toca nesses globals diretamente.
    """
    global _graph, _checkpointer_ctx
    async with _graph_lock:
        if _checkpointer_ctx is None:
            return
        ctx = _checkpointer_ctx
        _checkpointer_ctx = None
        _graph = None
        try:
            await ctx.__aexit__(None, None, None)
            logger.info("api/chat: checkpointer SQLite fechado")
        except Exception as exc:  # noqa: BLE001
            logger.warning("api/chat: erro ao fechar checkpointer: %s", exc)


async def awarm_graph() -> None:
    """Inicializa o grafo eagerly no startup (opt-in).

    Evita que a primeira request pague o custo de compilação (~3-5s).
    Falhas aqui não derrubam o servidor — apenas logam aviso.
    """
    try:
        await _get_graph()
    except Exception as exc:  # noqa: BLE001
        logger.warning("api/chat: warmup do grafo falhou (continuando): %s", exc)


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

    # Registra thread em vectora_sessions para que ListThreads a inclua
    # mesmo após reinicialização do servidor (o checkpointer LangGraph persiste
    # separadamente e não é consultado pelo endpoint de listagem).
    try:
        from vectora.api.handlers.threads import _upsert_session

        await _upsert_session(thread_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "api/chat: falha ao registrar thread em vectora_sessions: %s", exc
        )

    try:
        graph = await _get_graph()
    except Exception as exc:
        logger.exception("api/chat: erro ao inicializar grafo")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    config: dict[str, Any] = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": request.config.recursion_limit or 50,
    }

    human_msg = _build_human_message(request.content, request.attachments)

    events = graph.astream_events(
        {"messages": [human_msg]},
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

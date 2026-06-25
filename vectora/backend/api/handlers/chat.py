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

import base64
import contextlib
import json
import logging
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from backend.api.adapters import adapt_stream
from backend.api.schemas import (
    Attachment,
    AttachmentKind,
    ChatConfig,
    GetToolsResponse,
    ResumeChatRequest,
    StreamChatRequest,
    ToolSchema,
)
from backend.services import agent_factory
from backend.vtypes.context import ctx_from_config

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


def _detect_planning_mode(content: str) -> tuple[str, bool]:
    """Detecta prefixo /plan no início da mensagem.

    Retorna (texto_sem_prefixo, planning_mode). Case-insensitive.
    """
    stripped = content.lstrip()
    if stripped.lower().startswith("/plan"):
        remainder = stripped[5:].lstrip()
        return remainder, True
    return content, False


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

    parts: list[str | dict[str, Any]] = [{"type": "text", "text": content}]

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


def _prepend_text_context(msg: Any, block: str) -> Any:
    """Prepende um bloco de texto de contexto à HumanMessage (str ou multimodal).

    Preserva o conteúdo original: para texto puro, concatena; para conteúdo
    multimodal (lista de parts), insere uma part de texto no início.
    """
    from langchain_core.messages import HumanMessage

    content = getattr(msg, "content", None)
    if isinstance(content, str):
        return HumanMessage(content=f"{block}\n\n{content}")
    if isinstance(content, list):
        return HumanMessage(content=[{"type": "text", "text": block}, *content])
    return msg


# ---------------------------------------------------------------------------
# Lazy graph loader — delegado para src.graph
# ---------------------------------------------------------------------------


async def aclose_graph() -> None:
    """Fecha o grafo + checkpointer SQLite. Idempotente.

    Delegado para ``src.graph.aclose()`` — estado de lifecycle mantido lá.
    """
    await agent_factory.aclose()


async def awarm_graph() -> None:
    """Inicializa o grafo eagerly no startup (opt-in).

    Delegado para ``src.graph.awarm()``.
    """
    await agent_factory.awarm()


# ---------------------------------------------------------------------------
# StreamChat
# ---------------------------------------------------------------------------


def _user_id_from_request(http_request: Request) -> str:
    """Extrai o user_id do request autenticado para o namespace de memória.

    O AuthMiddleware injeta ``request.state.user`` quando o token é válido.
    Sem usuário (modo CLI/root local), usa ``"local"`` — espelhando o
    fallback de ``handlers/memory.py::_get_user_id``, garantindo que as
    memórias gravadas pelo agente apareçam na aba Memória.
    """
    user = getattr(http_request.state, "user", None)
    if user is not None and getattr(user, "id", None):
        return str(user.id)
    return "local"


def _resolve_workspace_id(requested: str, thread_id: str, user_id: str) -> str:
    """Resolve o workspace da sessão.

    Com ``requested``, mantém a pasta escolhida pelo cliente. Sem ela, reusa o
    workspace ativo do usuário; só quando não há ativo registra o workspace
    padrão da sessão em ``~/Documents/vectora/<thread_id>``. Degrada para
    string vazia se a resolução falhar — nesse caso as tools usam o fallback
    de diretório atual.
    """
    if requested:
        return requested
    try:
        from backend.services.workspace import workspace_registry

        # Reusa o workspace ativo do usuário em vez de registrar um por thread —
        # caso contrário cada conversa cria um ~/Documents/vectora/<thread_id>,
        # poluindo o seletor de workspaces.
        active = workspace_registry.get_active(user_id)
        if active is not None:
            return active.id

        ws = workspace_registry.get_or_create_session_workspace(thread_id, user_id)
        workspace_registry.set_active(ws.id, user_id)
        return ws.id
    except Exception:
        logger.warning(
            "api/chat: falha ao criar workspace de sessão para %s", thread_id
        )
        return ""


def _user_name_from_request(http_request: Request) -> str:
    """Extrai o nome do usuário autenticado, ou vazio em modo CLI/anônimo."""
    user = getattr(http_request.state, "user", None)
    if user is None:
        return ""
    return str(getattr(user, "name", "") or "").strip()


def _build_configurable(
    config: ChatConfig,
    thread_id: str,
    user_id: str,
    user_name: str = "",
) -> dict[str, Any]:
    """Monta o dict ``configurable`` do RunnableConfig a partir do ChatConfig.

    Campos opcionais (workspace, prompt custom, modo de permissão, esforço de
    raciocínio, idioma, nome do usuário) só entram quando preenchidos — nós e o
    ``hitl_check`` aplicam seus defaults quando ausentes.

    O ``user_name`` e ``language`` são consumidos pelo orchestrator para
    personalizar o system prompt do agente (tratar pelo nome, responder no
    idioma preferido).
    """
    configurable: dict[str, Any] = {
        "thread_id": thread_id,
        "user_id": user_id,
    }
    if config.model:
        # O seletor de modelo envia "provider:model" (ex.:
        # "cohere:command-a-03-2025"). O grafo (singleton) é compilado com um
        # modelo configurável via init_chat_model; passar "model" no
        # configurable troca o modelo por request. O init_chat_model espera o
        # provider canônico com underscore ("google_genai"), enquanto a UI usa
        # hífen ("google-genai") — normalizamos só o segmento de provider.
        spec = config.model
        prov, sep, name = spec.partition(":")
        configurable["model"] = f"{prov.replace('-', '_')}:{name}" if sep else spec
    if config.workspace_id:
        configurable["workspace_id"] = config.workspace_id
    if config.custom_system_prompt:
        configurable["custom_system_prompt"] = config.custom_system_prompt
    if config.permission_mode:
        configurable["permission_mode"] = config.permission_mode
    if config.reasoning_effort:
        configurable["reasoning_effort"] = config.reasoning_effort
    # Idioma: lido cru do locale do SO (Python `os`/`locale`), repassado
    # sem normalização. O dict de mapeamento foi removido — modelos
    # modernos interpretam BCP-47/POSIX nativamente.
    from backend.agents._identity import detect_system_language

    sys_lang = detect_system_language()
    if sys_lang:
        configurable["language"] = sys_lang
    if user_name:
        configurable["user_name"] = user_name
    return configurable


@router.post("/vectora.chat.v1.ChatService/StreamChat")
async def stream_chat(
    request: StreamChatRequest, http_request: Request
) -> StreamingResponse:
    """Inicia ou continua uma conversa — retorna SSE stream.

    Se `thread_id` estiver vazio, cria uma nova thread e emite o ThreadEvent
    como primeiro pacote do stream. O cliente deve armazenar o thread_id
    recebido para continuar a conversa.
    """
    thread_id = request.thread_id or str(uuid.uuid4())

    # user_id alimenta o namespace de memória (user:<id>) — precisa bater com o
    # namespace lido por GET /memory (handlers/memory.py). Sem isso, save_memory
    # caía em session_<thread_id> e a aba Memória ficava vazia.
    user_id = _user_id_from_request(http_request)

    chat_mode = request.config.chat_mode

    # Modo Chat: conversacional puro — sem workspace/folders. Não resolve nem
    # materializa workspace; a sessão é gravada como mode="chat".
    if chat_mode:
        request.config.workspace_id = ""
        workspace_id = ""
    else:
        # Resolve o workspace da sessão (cria o padrão em Documents/src/<id>
        # quando o cliente não escolheu uma pasta) e fixa no config da request.
        workspace_id = _resolve_workspace_id(
            request.config.workspace_id, thread_id, user_id
        )
        request.config.workspace_id = workspace_id

        # Cria vectora.toml e .vectora/ na pasta do workspace, se ainda não
        # existirem (ex: workspace de sessão cuja pasta só foi materializada
        # após uma operação de fs em turno anterior). Idempotente e degrada
        # silenciosamente — nunca impede o início da sessão.
        if workspace_id:
            try:
                from pathlib import Path

                from backend.services.workspace import workspace_registry

                ws = workspace_registry.get(workspace_id)
                if ws is not None and Path(ws.cwd).is_dir():
                    workspace_registry.ensure_local_files(ws)
            except Exception:
                logger.warning(
                    "api/chat: falha ao garantir arquivos do workspace %s",
                    workspace_id,
                )

    # Registra thread em vectora_sessions para que ListThreads a inclua
    # mesmo após reinicialização do servidor (o checkpointer LangGraph persiste
    # separadamente e não é consultado pelo endpoint de listagem). Persiste o
    # workspace e o modo (chat/dev) para que a sidebar filtre e restaure a pasta.
    try:
        from backend.api.handlers.threads import _upsert_session

        await _upsert_session(
            thread_id,
            workspace_id=workspace_id or None,
            mode="chat" if chat_mode else "dev",
        )
    except Exception as exc:
        logger.warning(
            "api/chat: falha ao registrar thread em vectora_sessions: %s", exc
        )

    user_name = _user_name_from_request(http_request)

    # Planning mode: /plan prefix ativa instrução de planejamento multi-step
    planning_content, planning_mode = _detect_planning_mode(request.content)
    if planning_mode:
        request.content = planning_content

    configurable = _build_configurable(
        request.config, thread_id, user_id, user_name=user_name
    )
    if planning_mode:
        configurable["planning_mode"] = True

    try:
        # Troca de modelo por request: o grafo é cacheado por modelo escolhido
        # (configurable["model"] já normalizado para "provider:model"). Sem
        # escolha, usa o grafo do modelo padrão. chat_mode usa um grafo separado
        # com toolset conversacional (CHAT_TOOLS).
        graph = await agent_factory.get_user_agent(
            user_id, model=configurable.get("model", ""), chat_mode=chat_mode
        )
    except Exception as exc:
        logger.exception("api/chat: erro ao inicializar grafo")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    from backend.services.usage import usage_tracker

    usage_tracker.record(user_id)

    config: dict[str, Any] = {
        "configurable": configurable,
        "recursion_limit": request.config.recursion_limit or 50,
    }

    human_msg = _build_human_message(request.content, request.attachments)

    # Planning mode: injeta instrução de planejamento no HumanMessage
    if planning_mode:
        planning_prefix = (
            "[MODO PLANEJAMENTO ATIVO] Antes de executar qualquer ação:\n"
            "1. Analise a tarefa e crie um plano de 3-5 passos via create_artifact "
            "(tipo task_list, slug: plano-<slug-descritivo>).\n"
            "2. Aguarde confirmação do usuário antes de executar.\n"
            "3. Execute cada passo marcando-o com update_plan_item conforme avança.\n\n"
        )
        human_msg = _prepend_text_context(human_msg, planning_prefix)

    # Pins (WB-1): injeta o conteúdo dos arquivos fixados no turno, para que
    # "fixar" mantenha o arquivo no contexto do agente. Só em modo Dev (chat
    # puro não tem workspace). Defensivo — falha aqui nunca impede a conversa.
    if not chat_mode and workspace_id:
        try:
            from backend.api.handlers.threads import build_pinned_context
            from backend.services.workspace import workspace_registry

            ws = workspace_registry.get(workspace_id)
            if ws is not None:
                pinned = await build_pinned_context(thread_id, ws.cwd)
                if pinned:
                    human_msg = _prepend_text_context(human_msg, pinned)
        except Exception:
            logger.warning("api/chat: falha ao injetar pinned_files", exc_info=True)

    events = graph.astream_events(
        {"messages": [human_msg]},
        config=config,
        context=ctx_from_config(config),
        version="v2",
    )

    return StreamingResponse(
        adapt_stream(events, thread_id, workspace_id=workspace_id or None),
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
async def resume_chat(
    request: ResumeChatRequest, http_request: Request
) -> StreamingResponse:
    """Retoma uma execução pausada por HITL.

    `decision` pode ser:
    - ``"approve"`` — executa a tool com os args originais
    - ``"reject"`` — cancela; o agente recebe feedback de rejeição
    - ``"edit:<args_json>"`` — executa com args modificados
    """
    from langgraph.types import Command

    resume_user_id = _user_id_from_request(http_request)
    try:
        graph = await agent_factory.get_user_agent(resume_user_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    config: dict[str, Any] = {
        "configurable": {
            "thread_id": request.thread_id,
            "user_id": resume_user_id,
        },
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
        context=ctx_from_config(config),
        version="v2",
    )

    return StreamingResponse(
        adapt_stream(events, request.thread_id, workspace_id=None),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---------------------------------------------------------------------------
# GetTools
# ---------------------------------------------------------------------------


@router.get("/vectora.chat.v1.ChatService/GetTools")
async def get_tools(http_request: Request) -> GetToolsResponse:
    """Retorna o schema das ferramentas disponíveis para o usuário autenticado.

    Reflete a política de tools (deny por usuário) + as tools dos servidores MCP
    do usuário — o mesmo toolset que o agente recebe (S4/S7).
    """
    try:
        from backend.services.tool_resolver import resolve_tools

        resolved = await resolve_tools(_user_id_from_request(http_request))
    except Exception as exc:
        logger.warning("api/chat: não foi possível resolver tools: %s", exc)
        return GetToolsResponse(tools=[])

    tools: list[ToolSchema] = []
    for t in resolved:
        meta = getattr(t, "extras", None) or getattr(t, "metadata", None) or {}
        render_hint = meta.get("render_hint", "json")

        args_schema = "{}"
        if hasattr(t, "args_schema") and t.args_schema:
            with contextlib.suppress(Exception):
                args_schema = json.dumps(t.args_schema.model_json_schema())

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

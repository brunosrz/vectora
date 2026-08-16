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
import os
import uuid
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from backend.api.native_stream import stream_engine_events
from backend.api.schemas import (
    Attachment,
    AttachmentKind,
    ChatConfig,
    DoneEvent,
    ErrorEvent,
    GetToolsResponse,
    ResumeChatRequest,
    StreamChatRequest,
    ThreadEvent,
    ToolSchema,
    TranscribeAudioRequest,
    TranscribeAudioResponse,
    encode_event,
)
from backend.engine.conversation_loop import (
    LoopConfig,
    resume_conversation,
    run_conversation,
)
from backend.engine.hitl import should_require_approval
from backend.llm.fallback_chat_client import FallbackChatClient
from backend.services import agent_factory
from backend.settings import TOOL_CALLING_INCOMPATIBLE_MODELS, VISION_CAPABLE_PROVIDERS
from backend.tools.subagent_delegate import SubagentDeps
from backend.vtypes.context import ctx_from_config
from backend.vtypes.message import ContentBlock, MessageRole, VMessage, text_message

if TYPE_CHECKING:
    from backend.engine.stream_events import EventSink

logger = logging.getLogger(__name__)

router = APIRouter()

#: permission_mode do último turno de cada thread — resume_chat (HITL) precisa
#: reidratar o MESMO ``ToolContext`` que ``stream_chat`` usou nesse turno,
#: já que o motor nativo reavalia ``should_require_approval`` dinamicamente a
#: partir de ``ctx.permission_mode`` a cada lote de tool calls, sem estado de
#: grafo compilado para carregar esse valor.
_thread_permission_mode: dict[str, str] = {}

#: (model, chat_mode, workspace_id) do último turno de cada thread —
#: resume_chat precisa resolver o MESMO ``NativeAgent`` (tools/subagentes) e
#: o mesmo ``FallbackChatClient.primary_model_id`` que ``stream_chat`` usou
#: nesse turno; sem isso, o resume roda com o modelo/toolset padrão em vez
#: do que o usuário de fato selecionou.
_thread_graph_selector: dict[str, dict[str, Any]] = {}

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

#: Extensão de fallback por MIME quando `att.name` não carrega uma (ex.:
#: screenshot colado direto do clipboard, sem nome de arquivo real).
_EXT_BY_MIME: dict[str, str] = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/svg+xml": ".svg",
}


def _mime_to_lang(filename: str) -> str:
    """Detecta a linguagem de programação pela extensão do arquivo.

    Retorna string vazia se não reconhecido (ex: PDF, binários).
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return _EXT_TO_LANG.get(ext, "")


def _resolve_provider(model_spec: str) -> str:
    """Extrai o provider (``google_genai``, ``cohere`` etc.) do valor já
    normalizado em ``configurable["model"]``. Sem escolha explícita de
    modelo na request, espelha o fallback de
    ``services/utils.py::load_llm`` (provider ativo do runtime/env).
    """
    if model_spec:
        provider, _, _ = model_spec.partition(":")
        return provider

    from backend.workspace.runtime_settings import runtime_settings

    return (os.getenv("LLM_PROVIDER") or runtime_settings.active_provider).replace(
        "-", "_"
    )


async def _model_supports_vision(model_spec: str) -> bool:
    """Capability de visão do modelo escolhido — provider fixo
    (``VISION_CAPABLE_PROVIDERS``) pros diretos, mas OpenRouter varia por
    modelo servido (alguns processam imagem, outros não), então delega pro
    catálogo público em vez de bloquear o provider inteiro."""
    provider = _resolve_provider(model_spec)
    if provider in VISION_CAPABLE_PROVIDERS:
        return True
    if provider == "openrouter":
        from backend.api.handlers.provider_routing import (
            openrouter_model_supports_image,
        )

        _, _, model_id = model_spec.partition(":")
        return await openrouter_model_supports_image(model_id or model_spec)
    return False


async def _resolve_image_fallback_model() -> str | None:
    """Modelo de fallback configurado pra anexos de imagem quando o ativo
    não processa (`runtime_settings["image_fallback_model"]`, vazio por
    padrão — sem fallback configurado, o comportamento antigo de bloquear
    o envio é preservado). Devolve `None` se não configurado, ou se o
    próprio fallback também não suporta visão (config inconsistente não
    deve criar um loop de bloqueio disfarçado de fallback)."""
    from backend.workspace.runtime_settings import runtime_settings

    spec = runtime_settings.get("image_fallback_model")
    if not spec or not isinstance(spec, str):
        return None
    if not await _model_supports_vision(spec):
        return None
    return spec


async def _model_no_vision_stream(thread_id: str) -> AsyncGenerator[str]:
    """Stream de um único erro — mensagem tem imagem anexada mas o provider
    resolvido não aceita conteúdo multimodal (ex.: Cohere, Ollama). Evita
    deixar a exceção crua da API do provider (ex.: Cohere BadRequestError
    "image content is not supported") vazar pro usuário como erro genérico.
    """
    yield encode_event(ThreadEvent(thread_id=thread_id))
    yield encode_event(
        ErrorEvent(
            message="Modelo não suporta imagens anexadas.",
            code="MODEL_NO_VISION",
        )
    )
    yield encode_event(DoneEvent(thread_id=thread_id))


async def _model_tool_incompatible_stream(thread_id: str) -> AsyncGenerator[str]:
    """Stream de um único erro — modelo escolhido rejeita replay de tool_calls
    no histórico (ver ``TOOL_CALLING_INCOMPATIBLE_MODELS``) e o modo atual
    (code mode) sempre usa tools. Rejeita cedo em vez de deixar o
    ``QuotaExhaustedError``/400 cru do provider estourar no meio do stream.
    """
    yield encode_event(ThreadEvent(thread_id=thread_id))
    yield encode_event(
        ErrorEvent(
            message="Este modelo não suporta chamadas de ferramentas — indisponível no modo código.",
            code="MODEL_NO_TOOL_CALLING",
        )
    )
    yield encode_event(DoneEvent(thread_id=thread_id))


async def _model_not_allowed_stream(thread_id: str) -> AsyncGenerator[str]:
    """Stream de um único erro — modelo pedido não está em
    ``[agent].allowed_models`` do ``vectora.toml`` do workspace. A única
    barreira antes disso era o filtro client-side do seletor de modelo
    (``deployment-config.ts``); um client modificado (ou chamada direta à
    API) podia mandar qualquer ``model`` sem essa checagem server-side."""
    yield encode_event(ThreadEvent(thread_id=thread_id))
    yield encode_event(
        ErrorEvent(
            message="Este modelo não está na lista de modelos permitidos deste workspace.",
            code="MODEL_NOT_ALLOWED",
        )
    )
    yield encode_event(DoneEvent(thread_id=thread_id))


def _detect_planning_mode(content: str) -> tuple[str, bool]:
    """Detecta prefixo /plan no início da mensagem.

    Retorna (texto_sem_prefixo, planning_mode). Case-insensitive.
    """
    stripped = content.lstrip()
    if stripped.lower().startswith("/plan"):
        remainder = stripped[5:].lstrip()
        return remainder, True
    return content, False


async def _transcribe_attachment(att: Attachment) -> str:
    """Transcreve um anexo de áudio, devolvendo um bloco de texto pronto pra inserir.

    Falha de transcrição (sem chave configurada, erro de rede/API) nunca
    propaga — vira uma nota inline indicando que a transcrição não rodou,
    preservando o resto do turno.
    """
    from backend.llm.transcription import TranscriptionError, transcribe_audio

    try:
        audio_bytes = base64.b64decode(att.base64_data)
    except Exception:
        return f"\n[Áudio: {att.name} — não foi possível decodificar o arquivo]"

    try:
        transcript = await transcribe_audio(audio_bytes, att.name, att.mime_type)
    except TranscriptionError:
        logger.exception("chat: falha ao transcrever áudio %s", att.name)
        return f"\n[Áudio: {att.name} — falha ao transcrever]"

    return f"\n[Áudio: {att.name}]\n{transcript}"


#: Diretório onde anexos de imagem sobrevivem a restart do processo —
#: `additional_kwargs` do LangGraph fica só no checkpoint (não é servido
#: por nenhuma rota), então sem copiar o arquivo pra cá o histórico via
#: REST (`GET /threads/{id}/history`) nunca tem de onde buscar a imagem de
#: volta depois que o backend reinicia.
_CHAT_ATTACHMENTS_DIRNAME = "chat-attachments"


def _persist_image_attachment(thread_id: str, att: Attachment) -> str | None:
    """Copia o anexo de imagem pra ``~/.vectora/chat-attachments/<thread_id>/``
    e devolve a URL servível por `GET /threads/{thread_id}/attachments/{name}`.

    Falha de disco (permissão, sem espaço) nunca aborta o turno — a imagem
    já foi enviada ao provider via base64 inline; só a reexibição depois de
    um restart fica indisponível, o que é preferível a quebrar o chat.
    """
    from backend.settings import settings

    try:
        raw = base64.b64decode(att.base64_data)
        ext = Path(att.name).suffix or _EXT_BY_MIME.get(att.mime_type, "")
        filename = f"{uuid.uuid4().hex}{ext}"
        safe_thread = thread_id.replace("/", "").replace("\\", "").replace("..", "")
        target_dir = settings.vectora_home / _CHAT_ATTACHMENTS_DIRNAME / safe_thread
        target_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / filename).write_bytes(raw)
        return f"/threads/{safe_thread}/attachments/{filename}"
    except Exception:
        logger.exception(
            "chat: falha ao persistir anexo de imagem %s (thread=%s)",
            att.name,
            thread_id,
        )
        return None


async def _build_human_message(
    content: str, attachments: list[Attachment], thread_id: str
) -> Any:
    """Constrói HumanMessage com suporte a conteúdo multimodal.

    - Sem attachments → ``HumanMessage(content=str)`` simples
    - Imagem → content list com ``type=image_url`` (formato OpenAI); o
      arquivo também é copiado pra disco (`_persist_image_attachment`) pra
      sobreviver a um restart do backend, já que o inline base64 só existe
      dentro do checkpoint do LangGraph, que a API REST de histórico não lê.
    - Áudio → transcrito via Whisper (STT) e injetado como texto
    - Código/PDF/texto → injetado como bloco de código ou texto no content list

    O formato de ``content`` como lista é compatível com a maioria dos provedores
    multimodais (OpenAI, Anthropic, Google Gemini via LangChain).
    """
    from langchain_core.messages import HumanMessage

    if not attachments:
        return HumanMessage(content=content)

    parts: list[str | dict[str, Any]] = [{"type": "text", "text": content}]
    persisted_urls: dict[int, str | None] = {}

    for att in attachments:
        if att.kind == AttachmentKind.IMAGE:
            # Log de diagnóstico para imagens grandes
            try:
                # Truncamento defensivo: se a imagem for absurdamente grande (> 5MB),
                # logamos um erro e avisamos que pode haver instabilidade.
                # O limite do schema é 10MB, mas 5MB já é arriscado para o SQLite.
                img_size = len(base64.b64decode(att.base64_data))
                if img_size > 5 * 1024 * 1024:
                    logger.error(
                        "chat: imagem MUITO grande recebida: %s (%d bytes). Isso pode corromper o checkpointer SQLite.",
                        att.name,
                        img_size,
                    )
                elif img_size > 2 * 1024 * 1024:
                    logger.warning(
                        "chat: imagem grande recebida: %s (%d bytes)",
                        att.name,
                        img_size,
                    )
            except Exception:
                pass

            persisted_urls[id(att)] = _persist_image_attachment(thread_id, att)

            parts.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{att.mime_type};base64,{att.base64_data}"
                    },
                }
            )
        elif att.kind == AttachmentKind.AUDIO:
            parts.append({"type": "text", "text": await _transcribe_attachment(att)})
        else:
            # Código, PDF ou texto — decodifica e injeta como texto
            try:
                decoded = base64.b64decode(att.base64_data).decode(
                    "utf-8", errors="replace"
                )
            except Exception:
                decoded = "[conteúdo não pôde ser decodificado]"

            lang = _mime_to_lang(att.name)
            if lang:
                block = f"\n[Arquivo: {att.name}]\n```{lang}\n{decoded}\n```"
            else:
                block = f"\n[Arquivo: {att.name}]\n{decoded}"

            parts.append({"type": "text", "text": block})

    metadata = {}
    if attachments:
        metadata["attachments_meta"] = [
            {
                "name": att.name,
                "mimeType": att.mime_type,
                "kind": att.kind.value,
                "size": len(base64.b64decode(att.base64_data)),
                "url": persisted_urls.get(id(att)),
            }
            for att in attachments
        ]

    return HumanMessage(content=parts, additional_kwargs=metadata)


def _to_vmessage(msg: Any) -> VMessage:
    """Converte a ``HumanMessage`` do LangChain (produzida por
    ``_build_human_message``/``_prepend_text_context``) para ``VMessage`` do
    motor nativo — mesmo shape de ``content`` (string simples ou lista de
    parts multimodais), só reempacotado como ``ContentBlock``. Metadados de
    anexo (``additional_kwargs["attachments_meta"]``) não têm equivalente em
    ``VMessage`` ainda — gap documentado em
    ``backend/services/agent_factory.py::aget_thread_messages``: o anexo
    continua enviado ao provider e persistido em disco, só a miniatura não
    reaparece num reload de thread nativa.
    """
    content = getattr(msg, "content", "")
    blocks: list[ContentBlock] = []
    if isinstance(content, str):
        blocks.append(ContentBlock(kind="text", text=content))
    else:
        for part in content:
            if not isinstance(part, dict):
                continue
            if part.get("type") == "text":
                blocks.append(ContentBlock(kind="text", text=part.get("text", "")))
            elif part.get("type") == "image_url":
                url = (part.get("image_url") or {}).get("url", "")
                blocks.append(ContentBlock(kind="image_url", image_url=url))
    return VMessage(role=MessageRole.USER, content=blocks)


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


def _resolve_workspace_id(
    requested: str, thread_id: str, user_id: str, force_new: bool = False
) -> str:
    """Resolve o workspace da sessão.

    Com ``requested``, mantém a pasta escolhida pelo cliente. Sem ela, reusa o
    workspace ativo do usuário; só quando não há ativo registra o workspace
    padrão da sessão em ``~/Documents/vectora/<thread_id>``. Degrada para
    string vazia se a resolução falhar — nesse caso as tools usam o fallback
    de diretório atual.

    ``force_new`` — sinal explícito do cliente ("criar novo workspace para
    essa conversa" no modal de nova conversa, ver ``ChatConfig
    .create_new_workspace``). Pula o reuso do workspace ativo e vai direto
    pra ``get_or_create_session_workspace``, mesmo que exista um ativo —
    sem isso, ``requested`` vazio é ambíguo (sem opinião vs. "quero um novo
    de propósito") e o reuso sempre vence.
    """
    if requested:
        return requested
    try:
        from backend.workspace.workspace import workspace_registry

        if not force_new:
            # Reusa o workspace ativo do usuário em vez de registrar um por
            # thread — caso contrário cada conversa cria um
            # ~/Documents/vectora/<thread_id>, poluindo o seletor.
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


def _normalize_model_spec(spec: str) -> str:
    """Normaliza o segmento de provider de ``"provider:model"`` pra underscore.

    A UI e o ``vectora.toml`` usam hífen ("google-genai"); o
    ``init_chat_model`` espera o provider canônico com underscore
    ("google_genai"). Usada tanto pro ``configurable["model"]`` real quanto
    pra comparar contra ``allowed_models`` no mesmo formato.
    """
    prov, sep, name = spec.partition(":")
    return f"{prov.replace('-', '_')}:{name}" if sep else spec


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
        configurable["model"] = _normalize_model_spec(config.model)
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
    if config.fork_from_checkpoint_id:
        # Alvo de fork (SessionStore.set_branch_head) — resumir a partir de
        # um checkpoint_id anterior faz a thread ramificar dali ao processar
        # a nova mensagem, em vez de continuar do fim da branch atual.
        configurable["checkpoint_id"] = config.fork_from_checkpoint_id
    return configurable


def _apply_persisted_model_preference(config: ChatConfig, user_id: str) -> None:
    """Use the backend-persisted model when the request omits one.

    The browser cache is only an optimization; a reload can briefly construct
    a request before Zustand finishes hydration. The persisted preference is
    the authoritative value for that case and keeps provider selection aligned
    with the model shown by the backend.
    """
    if config.model:
        return
    from backend.workspace.runtime_settings import runtime_settings

    preference = runtime_settings.get_frontend_prefs(user_id).get("selectedModel")
    if isinstance(preference, str) and ":" in preference:
        config.model = preference


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
    _apply_persisted_model_preference(request.config, user_id)

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
            request.config.workspace_id,
            thread_id,
            user_id,
            force_new=request.config.create_new_workspace,
        )
        request.config.workspace_id = workspace_id

        # Cria vectora.toml e .vectora/ na pasta do workspace, se ainda não
        # existirem (ex: workspace de sessão cuja pasta só foi materializada
        # após uma operação de fs em turno anterior). Idempotente e degrada
        # silenciosamente — nunca impede o início da sessão.
        if workspace_id:
            try:
                from pathlib import Path

                from backend.workspace.workspace import workspace_registry

                ws = workspace_registry.get(workspace_id)
                if ws is not None and Path(ws.cwd).is_dir():
                    workspace_registry.ensure_local_files(ws)
            except Exception:
                logger.warning(
                    "api/chat: falha ao garantir arquivos do workspace %s",
                    workspace_id,
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

    # Usa o model spec BRUTO (pré-normalização de `_build_configurable`) —
    # `configurable["model"]` já converteu o provider pra underscore
    # (`_normalize_model_spec`, formato que o `init_chat_model` exige), mas
    # `VISION_CAPABLE_PROVIDERS`/`AVAILABLE_MODELS` usam a convenção com
    # hífen do resto de settings.py; comparar contra a forma normalizada
    # bloqueava até modelos com suporte real a visão (ex.: Gemini).
    has_image = any(att.kind == AttachmentKind.IMAGE for att in request.attachments)
    if has_image and not await _model_supports_vision(request.config.model):
        fallback_spec = await _resolve_image_fallback_model()
        if fallback_spec is None:
            return StreamingResponse(
                _model_no_vision_stream(thread_id),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
            )
        # Modelo ativo não processa imagem, mas há um fallback configurado
        # que processa — roteia pra ele nesta chamada em vez de bloquear o
        # envio. Só troca o `configurable["model"]` desta request; a
        # preferência do usuário no seletor não muda.
        configurable["model"] = _normalize_model_spec(fallback_spec)

    # Code mode sempre usa tools (ALL_TOOLS) — modelos que rejeitam replay de
    # tool_calls no histórico nunca funcionam aqui, mesmo na primeira
    # mensagem sem tool use ainda (a segunda falharia). Chat mode não é
    # bloqueado (decisão de produto, ver TOOL_CALLING_INCOMPATIBLE_MODELS).
    if (
        not chat_mode
        and configurable.get("model", "") in TOOL_CALLING_INCOMPATIBLE_MODELS
    ):
        return StreamingResponse(
            _model_tool_incompatible_stream(thread_id),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    # allowed_models do vectora.toml do workspace — fonte de verdade real,
    # não só o filtro do seletor de modelo no cliente (regra 8 CLAUDE.md).
    if not chat_mode and workspace_id:
        from backend.workspace.workspace import workspace_registry
        from backend.workspace.workspace_config import load_workspace_config

        ws = workspace_registry.get(workspace_id)
        if ws is not None:
            ws_config = load_workspace_config(ws.cwd)
            allowed_models = ws_config.agent.allowed_models if ws_config else None
            normalized_allowed = (
                {_normalize_model_spec(m) for m in allowed_models}
                if allowed_models
                else None
            )
            if (
                normalized_allowed
                and configurable.get("model", "") not in normalized_allowed
            ):
                return StreamingResponse(
                    _model_not_allowed_stream(thread_id),
                    media_type="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
                )

    # Troca de modelo por request: tools/subagentes/system prompt são
    # cacheados por (user, chat_mode, workspace) — não por modelo (o
    # ChatClient é resolvido por chamada via FallbackChatClient, dentro da
    # closure `run` abaixo). O permission_mode NÃO afeta o cache (HITL
    # dinâmico via ToolContext.permission_mode); guardamos o modo do turno
    # só para o resume reidratar o mesmo contexto (ver resume_chat).
    permission_mode = configurable.get("permission_mode", "ask")
    _thread_permission_mode[thread_id] = permission_mode
    selected_model = configurable.get("model", "")
    _thread_graph_selector[thread_id] = {
        "model": selected_model,
        "chat_mode": chat_mode,
        "workspace_id": workspace_id or None,
    }
    try:
        native_agent = await agent_factory.get_native_agent(
            user_id, chat_mode=chat_mode, workspace_id=workspace_id or None
        )
        session_store = await agent_factory.get_session_store()
    except Exception as exc:
        logger.exception("api/chat: erro ao inicializar o motor nativo")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    await session_store.create_session(
        thread_id,
        user_id=user_id,
        workspace_id=workspace_id or None,
        mode="chat" if chat_mode else "code",
        permission_mode=permission_mode,
    )

    # Registra thread em vectora_sessions e conta a mensagem do usuário —
    # é o usuário quem inicia a conversa, então a thread já é "real" (deve
    # aparecer em ListThreads e sobreviver a cleanup_empty_threads) a partir
    # daqui, mesmo que o assistente nunca chegue a responder (erro de auth/
    # quota/timeout do provider). `adapt_stream()` (ver `content_started`)
    # incrementa de novo no 1º token do assistente — o contador deixou de
    # significar "só resposta do assistente" e passou a significar "tem
    # pelo menos 1 mensagem real", que é o que list_threads/cleanup_
    # empty_threads precisam. Só thread sem NENHUMA mensagem (nem essa)
    # continua com message_count=0 e é limpa normalmente.
    try:
        from backend.api.handlers.threads import (
            _increment_message_count,
            _upsert_session,
        )

        await _upsert_session(
            thread_id,
            workspace_id=workspace_id or None,
            mode="chat" if chat_mode else "code",
        )
        await _increment_message_count(thread_id)
    except Exception as exc:
        logger.warning(
            "api/chat: falha ao registrar thread em vectora_sessions: %s", exc
        )

    from backend.services.usage import usage_tracker

    usage_tracker.record(user_id)

    config: dict[str, Any] = {
        "configurable": configurable,
        "recursion_limit": request.config.recursion_limit or 50,
    }

    human_msg = await _build_human_message(
        request.content, request.attachments, thread_id
    )

    # Planning mode: injeta instrução de planejamento no HumanMessage
    if planning_mode:
        planning_prefix = (
            "[PLANNING MODE ACTIVE] Before executing anything:\n"
            "1. Break the task into 3-5 concrete steps using `write_todos` "
            "(mark the first step as in_progress immediately).\n"
            "2. Wait for user confirmation before executing, unless the task "
            "is unambiguous and low-risk.\n"
            "3. Update each todo's status via `write_todos` as you progress — "
            "mark items completed immediately after finishing them, never batch.\n\n"
        )
        human_msg = _prepend_text_context(human_msg, planning_prefix)

    # Injeta o conteúdo dos arquivos fixados (pins) no turno, para que
    # "fixar" mantenha o arquivo no contexto do agente. Só em modo Dev (chat
    # puro não tem workspace). Defensivo — falha aqui nunca impede a conversa.
    if not chat_mode and workspace_id:
        try:
            from backend.api.handlers.threads import build_pinned_context
            from backend.workspace.workspace import workspace_registry

            ws = workspace_registry.get(workspace_id)
            if ws is not None:
                pinned = await build_pinned_context(thread_id, ws.cwd)
                if pinned:
                    human_msg = _prepend_text_context(human_msg, pinned)
        except Exception:
            logger.warning("api/chat: falha ao injetar pinned_files", exc_info=True)

    # Motor nativo relê o histórico da persistência a cada iteração do loop
    # (backend/engine/conversation_loop.py) — a mensagem do usuário precisa
    # estar gravada ANTES de `run_conversation` começar. Thread sem nenhuma
    # mensagem ainda (`get_branch_head_id` devolve None) recebe o system
    # prompt do agente como raiz da cadeia, mesmo padrão de
    # `backend/engine/subagents.py::_run_subagent_once`.
    user_msg = _to_vmessage(human_msg)
    if request.config.fork_from_checkpoint_id:
        # "Editar e reenviar"/"regenerar" — ramifica a partir de uma
        # mensagem anterior em vez de continuar do fim da branch atual; a
        # branch divergente anterior nunca é apagada (ver
        # SessionStore.set_branch_head).
        try:
            await session_store.set_branch_head(
                thread_id, int(request.config.fork_from_checkpoint_id)
            )
        except Exception:
            logger.warning(
                "api/chat: checkpoint_id de fork inválido para thread %s: %r",
                thread_id,
                request.config.fork_from_checkpoint_id,
            )
    parent_id = await session_store.get_branch_head_id(thread_id)
    if parent_id is None:
        parent_id = await session_store.append_message(
            thread_id, text_message(MessageRole.SYSTEM, native_agent.system_prompt)
        )
    await session_store.append_message(thread_id, user_msg, parent_message_id=parent_id)

    async def run(on_event: EventSink) -> str:
        chat_client = FallbackChatClient(primary_model_id=configurable.get("model", ""))
        run_ctx = ctx_from_config(config)
        run_ctx.store = await agent_factory.get_store()
        approval_gate = await agent_factory.get_approval_gate()
        loop_config = LoopConfig(max_iterations=request.config.recursion_limit or 50)
        if native_agent.subagent_catalog:
            # `delegate_to_subagent` (backend/tools/subagent_delegate.py) lê
            # essas dependências via ctx._extra — nunca aparecem no schema
            # exposto ao LLM. Sem isso a tool devolve erro tipado em vez de
            # delegar de verdade.
            run_ctx._extra["subagent_deps"] = SubagentDeps(
                catalog=native_agent.subagent_catalog,
                session_store=session_store,
                chat_client=chat_client,
                config=loop_config,
                on_event=on_event,
                should_require_approval=should_require_approval,
            )
        result = await run_conversation(
            session_store=session_store,
            chat_client=chat_client,
            tool_registry=native_agent.tool_registry,
            ctx=run_ctx,
            thread_id=thread_id,
            config=loop_config,
            on_event=on_event,
            should_require_approval=should_require_approval,
            approval_gate=approval_gate,
        )
        return result.stopped_reason

    return StreamingResponse(
        stream_engine_events(
            run,
            thread_id=thread_id,
            workspace_id=workspace_id or None,
            http_request=http_request,
            user_id=user_id,
        ),
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
    resume_user_id = _user_id_from_request(http_request)
    permission_mode = _thread_permission_mode.get(request.thread_id, "ask")
    selector = _thread_graph_selector.get(request.thread_id, {})
    selector_model = str(selector.get("model", "") or "")
    selector_chat_mode = bool(selector.get("chat_mode", False))
    selector_workspace_id = selector.get("workspace_id")

    if request.decision == "approve":
        decision = "approve"
        edited_args: dict[str, Any] | None = None
    elif request.decision == "reject":
        decision = "reject"
        edited_args = None
    elif request.decision.startswith("edit:"):
        decision = "edit"
        try:
            edited_args = json.loads(request.decision[5:])
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=400, detail=f"Invalid edit args: {exc}"
            ) from exc
    else:
        raise HTTPException(
            status_code=400, detail=f"Unknown decision: {request.decision!r}"
        )

    try:
        native_agent = await agent_factory.get_native_agent(
            resume_user_id,
            chat_mode=selector_chat_mode,
            workspace_id=selector_workspace_id,
        )
        session_store = await agent_factory.get_session_store()
        approval_gate = await agent_factory.get_approval_gate()
    except Exception as exc:
        logger.exception("api/chat: erro ao inicializar o motor nativo (resume)")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    # permission_mode entra no configurable para que ctx_from_config o carregue
    # ao ToolContext — o HITL dinâmico reavalia o gate no resume com o MESMO
    # modo do turno original (senão uma 2ª tool destrutiva no mesmo turno seria
    # avaliada como "ask" e pausaria indevidamente num turno em modo "plan").
    config: dict[str, Any] = {
        "configurable": {
            "thread_id": request.thread_id,
            "user_id": resume_user_id,
            "permission_mode": permission_mode,
            "workspace_id": selector_workspace_id or "",
            "model": selector_model,
        },
        "recursion_limit": 50,
    }

    async def run(on_event: EventSink) -> str:
        run_ctx = ctx_from_config(config)
        run_ctx.store = await agent_factory.get_store()
        resumed = await resume_conversation(
            session_store=session_store,
            tool_registry=native_agent.tool_registry,
            ctx=run_ctx,
            thread_id=request.thread_id,
            decision=decision,
            edited_args=edited_args,
            approval_gate=approval_gate,
            on_event=on_event,
        )
        if not resumed:
            return "noop"
        chat_client = FallbackChatClient(primary_model_id=selector_model)
        loop_config = LoopConfig(max_iterations=50)
        if native_agent.subagent_catalog:
            run_ctx._extra["subagent_deps"] = SubagentDeps(
                catalog=native_agent.subagent_catalog,
                session_store=session_store,
                chat_client=chat_client,
                config=loop_config,
                on_event=on_event,
                should_require_approval=should_require_approval,
            )
        result = await run_conversation(
            session_store=session_store,
            chat_client=chat_client,
            tool_registry=native_agent.tool_registry,
            ctx=run_ctx,
            thread_id=request.thread_id,
            config=loop_config,
            on_event=on_event,
            should_require_approval=should_require_approval,
            approval_gate=approval_gate,
        )
        return result.stopped_reason

    return StreamingResponse(
        stream_engine_events(
            run,
            thread_id=request.thread_id,
            workspace_id=selector_workspace_id,
            http_request=http_request,
            user_id=resume_user_id,
        ),
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


# ---------------------------------------------------------------------------
# TranscribeAudio
# ---------------------------------------------------------------------------


@router.post("/vectora.chat.v1.ChatService/TranscribeAudio")
async def transcribe_audio_endpoint(
    request: TranscribeAudioRequest,
) -> TranscribeAudioResponse:
    """Transcreve um dictado de voz gravado no cliente (MediaRecorder).

    Fallback pro ditado quando a Web Speech API do browser não está
    disponível — caso do Electron/Chromium, que não embarca a chave de voz
    proprietária do Google que o Chrome tem.
    """
    from backend.llm.transcription import TranscriptionError, transcribe_audio

    try:
        audio_bytes = base64.b64decode(request.audio_base64)
    except Exception as exc:
        raise HTTPException(status_code=422, detail="áudio em base64 inválido") from exc

    try:
        text = await transcribe_audio(audio_bytes, request.filename, request.mime_type)
    except TranscriptionError as exc:
        logger.exception("chat: falha ao transcrever ditado de voz")
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return TranscribeAudioResponse(text=text)

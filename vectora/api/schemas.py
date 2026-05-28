"""Schemas Pydantic da API de chat — espelho do proto vectora/chat/v1/chat.proto.

Usados como request/response models do FastAPI e como tipos internos dos
handlers. Em produção com buf + grpcio, estes modelos poderiam ser gerados
automaticamente; aqui são mantidos manualmente para eliminar a dependência
de build-time durante desenvolvimento.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


class ChatConfig(BaseModel):
    model: str = ""
    llm_provider: str = ""
    recursion_limit: int = 50
    workspace_id: str = ""
    custom_system_prompt: str = ""  # L4 — instrução personalizada por usuário


# ---------------------------------------------------------------------------
# Attachments (F1 — File Handling)
# ---------------------------------------------------------------------------


class AttachmentKind(str, Enum):
    """Tipo semântico do attachment — determina como o backend o injeta na mensagem."""

    IMAGE = "image"  # imagem → image_url part (multimodal)
    PDF = "pdf"  # PDF → texto decodificado
    CODE = "code"  # código → bloco de código com linguagem detectada
    TEXT = "text"  # texto genérico → injetado como texto


class Attachment(BaseModel):
    """Arquivo anexado a uma mensagem pelo usuário.

    ``base64_data`` armazena o conteúdo em base64 puro (sem prefixo data URL).
    O frontend usa ``fileToBase64()`` que já remove o prefixo ``data:...;base64,``.
    """

    kind: AttachmentKind
    name: str
    mime_type: str
    base64_data: str


# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------


class StreamChatRequest(BaseModel):
    thread_id: str = ""  # vazio → cria nova thread
    content: str
    config: ChatConfig = Field(default_factory=ChatConfig)
    attachments: list[Attachment] = Field(default_factory=list)


class ResumeChatRequest(BaseModel):
    thread_id: str
    interrupt_id: str
    decision: str  # "approve" | "reject" | "edit:<args_json>"


class CreateThreadRequest(BaseModel):
    pass


class GetThreadRequest(BaseModel):
    thread_id: str


class ListThreadsRequest(BaseModel):
    limit: int = 50


class DeleteThreadRequest(BaseModel):
    thread_id: str


class UpdateThreadRequest(BaseModel):
    thread_id: str
    title: str = ""


class GetHistoryRequest(BaseModel):
    thread_id: str


# ---------------------------------------------------------------------------
# Eventos de streaming (oneof StreamChatEvent)
# ---------------------------------------------------------------------------


class ThreadEvent(BaseModel):
    thread_id: str


class TokenEvent(BaseModel):
    content: str
    node: str = ""


class ToolCallEvent(BaseModel):
    tool_name: str
    tool_call_id: str
    args_json: str
    render_hint: str = "json"
    category: str = "general"
    destructive: bool = False
    icon: str = "tool"


class ToolResultEvent(BaseModel):
    tool_call_id: str
    content_json: str
    is_error: bool = False


class NodeEvent(BaseModel):
    node: str
    status: Literal["started", "finished"]
    duration_ms: int = 0
    node_label: str = ""

    @model_validator(mode="after")
    def _fill_node_label(self) -> NodeEvent:
        if not self.node_label and self.node:
            from vectora.api.node_labels import get_node_label

            self.node_label = get_node_label(self.node)
        return self


class ThinkingEvent(BaseModel):
    """Raciocínio do orchestrator — visível para o usuário como bloco 'Thinking'."""

    reason: str
    action: str = "respond"
    delegate_to: str | None = None
    task_query: str | None = None


class UIMetricsEvent(BaseModel):
    last_node: str = ""
    last_node_ms: int = 0
    rag_hits: int = 0
    rag_misses: int = 0
    tool_calls: dict[str, int] = {}


class HITLEvent(BaseModel):
    tool_name: str
    args_json: str
    interrupt_id: str


class ErrorEvent(BaseModel):
    message: str
    code: str = "INTERNAL"


class DoneEvent(BaseModel):
    thread_id: str
    run_id: str = ""


# ---------------------------------------------------------------------------
# Envelope de streaming
# ---------------------------------------------------------------------------

# Cada linha do stream SSE é: data: <StreamChatEvent JSON>
# O campo "type" é o discriminator (equivalente ao oneof do proto).

StreamChatEventPayload = (
    ThreadEvent
    | TokenEvent
    | ToolCallEvent
    | ToolResultEvent
    | NodeEvent
    | UIMetricsEvent
    | HITLEvent
    | ThinkingEvent
    | ErrorEvent
    | DoneEvent
)

_TYPE_MAP: dict[type, str] = {
    ThreadEvent: "thread",
    TokenEvent: "token",
    ToolCallEvent: "tool_call",
    ToolResultEvent: "tool_result",
    NodeEvent: "node",
    UIMetricsEvent: "ui_metrics",
    HITLEvent: "hitl",
    ThinkingEvent: "thinking",
    ErrorEvent: "error",
    DoneEvent: "done",
}


def encode_event(payload: StreamChatEventPayload) -> str:
    """Serializa um evento para uma linha SSE: ``data: {...}\\n\\n``."""
    import json

    event_type = _TYPE_MAP[type(payload)]
    data = {"type": event_type, **payload.model_dump()}
    return f"data: {json.dumps(data)}\n\n"


# ---------------------------------------------------------------------------
# Thread management
# ---------------------------------------------------------------------------


class Thread(BaseModel):
    id: str
    created_at: str
    updated_at: str
    title: str = ""


class HistoryMessage(BaseModel):
    role: str
    content: str
    created_at: str = ""


class ListThreadsResponse(BaseModel):
    threads: list[Thread]


class GetHistoryResponse(BaseModel):
    messages: list[HistoryMessage]


# ---------------------------------------------------------------------------
# Tools schema (autodescoberta)
# ---------------------------------------------------------------------------


class ToolSchema(BaseModel):
    name: str
    description: str
    render_hint: str = "json"
    category: str = "general"
    destructive: bool = False
    icon: str = "tool"
    args_schema_json: str = "{}"


class GetToolsResponse(BaseModel):
    tools: list[ToolSchema]


# ---------------------------------------------------------------------------
# Auth schemas (Bloco C)
# ---------------------------------------------------------------------------


class SignupRequest(BaseModel):
    email: str
    password: str


class SigninRequest(BaseModel):
    email: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str = ""


class SignoutRequest(BaseModel):
    refresh_token: str = ""


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class UserResponse(BaseModel):
    id: str
    email: str
    role: str
    created_at: str
    last_login_at: str | None = None

    @classmethod
    def from_user(cls, user: Any) -> UserResponse:
        return cls(
            id=user.id,
            email=user.email,
            role=user.role,
            created_at=user.created_at,
            last_login_at=getattr(user, "last_login_at", None),
        )


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class HasUsersResponse(BaseModel):
    exists: bool


class UserListResponse(BaseModel):
    users: list[UserResponse]


class UpdateRoleRequest(BaseModel):
    role: str


class AuditEntry(BaseModel):
    id: str
    user_id: str | None = None
    action: str
    target_type: str | None = None
    target_id: str | None = None
    timestamp: str
    ip: str = ""
    success: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class EnvOverrideRequest(BaseModel):
    key: str
    value: str

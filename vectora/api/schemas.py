"""Schemas Pydantic da API de chat — espelho do proto vectora/chat/v1/chat.proto.

Usados como request/response models do FastAPI e como tipos internos dos
handlers. Em produção com buf + grpcio, estes modelos poderiam ser gerados
automaticamente; aqui são mantidos manualmente para eliminar a dependência
de build-time durante desenvolvimento.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


class ChatConfig(BaseModel):
    model: str = ""
    llm_provider: str = ""
    recursion_limit: int = 50
    workspace_id: str = ""


# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------


class StreamChatRequest(BaseModel):
    thread_id: str = ""  # vazio → cria nova thread
    content: str
    config: ChatConfig = Field(default_factory=ChatConfig)


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

"""Converte eventos do LangGraph (astream_events v2) em StreamChatEvent.

O LangGraph emite eventos do tipo:
    {"event": "on_chat_model_stream", "data": {"chunk": AIMessageChunk(...)}, ...}
    {"event": "on_tool_start", "data": {"input": {...}}, "name": "web_search", ...}
    ...

Este módulo mapeia esses eventos para os nossos tipos Pydantic e serializa
para o formato SSE (data: {...}\\n\\n) usado pelo endpoint /StreamChat.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from vectora.api.schemas import (
    DoneEvent,
    ErrorEvent,
    NodeEvent,
    StreamChatEventPayload,
    TokenEvent,
    ToolCallEvent,
    ToolResultEvent,
    UIMetricsEvent,
    encode_event,
)

logger = logging.getLogger(__name__)

# Mapeamento de nome de tool → render_hint (lido dos metadados da tool).
# Populado lazily pelo loader de tools — evita importar ALL_TOOLS no startup.
_render_hint_cache: dict[str, str] = {}


def _get_render_hint(tool_name: str) -> str:
    """Retorna o render_hint registrado para a tool, ou 'json' como fallback."""
    if not _render_hint_cache:
        try:
            from vectora.nodes.tools import ALL_TOOLS

            for t in ALL_TOOLS:
                hint = (getattr(t, "metadata", None) or {}).get("render_hint", "json")
                _render_hint_cache[t.name] = hint
        except Exception:
            pass
    return _render_hint_cache.get(tool_name, "json")


# ---------------------------------------------------------------------------
# Nós que emitem tokens (sub-grafos podem ter nomes diferentes)
# ---------------------------------------------------------------------------
_STREAMING_NODES = {
    "invoke_llm",
    "orchestrator",
    "search_agent",
    "coder_agent",
    "rag_agent",
}


def langgraph_event_to_payload(
    event: dict[str, Any],
) -> StreamChatEventPayload | None:
    """Converte um evento LangGraph em nosso StreamChatEventPayload.

    Retorna None se o evento não deve ser transmitido ao cliente
    (ex.: eventos internos de infraestrutura do grafo).
    """
    kind: str = event.get("event", "")
    name: str = event.get("name", "")
    data: dict[str, Any] = event.get("data", {})

    # ── Tokens de texto do LLM ────────────────────────────────────────────
    if kind == "on_chat_model_stream":
        chunk = data.get("chunk")
        if chunk is None:
            return None
        # AIMessageChunk tem .content (str ou list[dict])
        content = getattr(chunk, "content", "")
        if isinstance(content, list):
            # Formato multimodal: pegar só os blocos de texto
            content = "".join(b.get("text", "") for b in content if isinstance(b, dict))
        if not content:
            return None
        # Filtrar nós que não deveriam emitir tokens pro cliente
        # (ex.: chamadas LLM internas de julgamento/curadoria)
        run_name: str = event.get("run_name", "")
        return TokenEvent(content=content, node=run_name or name)

    # ── Início de tool call ───────────────────────────────────────────────
    if kind == "on_tool_start":
        tool_input = data.get("input", {})
        args_json = (
            json.dumps(tool_input) if isinstance(tool_input, dict) else str(tool_input)
        )
        # tool_call_id pode estar nos metadados ou no run_id
        call_id: str = event.get("run_id", "")
        return ToolCallEvent(
            tool_name=name,
            tool_call_id=call_id,
            args_json=args_json,
            render_hint=_get_render_hint(name),
        )

    # ── Resultado de tool ─────────────────────────────────────────────────
    if kind == "on_tool_end":
        output = data.get("output", "")
        call_id = event.get("run_id", "")
        # output pode ser ToolMessage, str, dict, etc.
        if hasattr(output, "content"):
            raw = output.content
        elif isinstance(output, dict):
            raw = json.dumps(output)
        else:
            raw = str(output)

        is_error = False
        if hasattr(output, "status"):
            is_error = output.status == "error"

        content_json = raw if isinstance(raw, str) else json.dumps(raw)
        return ToolResultEvent(
            tool_call_id=call_id,
            content_json=content_json,
            is_error=is_error,
        )

    # ── Início / fim de nó do grafo ───────────────────────────────────────
    if kind == "on_chain_start" and name not in ("", "LangGraph"):
        return NodeEvent(node=name, status="started")

    if kind == "on_chain_end" and name not in ("", "LangGraph"):
        # duration_ms não vem direto no evento; calculado pelo handler
        return NodeEvent(node=name, status="finished")

    return None


def adapt_stream(
    events: Any,
    thread_id: str,
) -> Any:
    """AsyncGenerator que converte o stream de eventos LangGraph em linhas SSE.

    Yields:
        str — linhas ``data: {...}\\n\\n`` prontas para StreamingResponse.
    """

    async def _gen() -> Any:
        # 1º evento: thread_id
        from vectora.api.schemas import ThreadEvent

        yield encode_event(ThreadEvent(thread_id=thread_id))

        node_start_times: dict[str, float] = {}
        import time

        try:
            async for event in events:
                kind = event.get("event", "")
                name = event.get("name", "")

                # Rastreia tempo de início dos nós para calcular duration_ms
                if kind == "on_chain_start":
                    node_start_times[name] = time.monotonic()

                payload = langgraph_event_to_payload(event)
                if payload is None:
                    continue

                # Injeta duration_ms nos NodeEvent de fim
                if isinstance(payload, NodeEvent) and payload.status == "finished":
                    start = node_start_times.pop(name, None)
                    if start is not None:
                        payload = payload.model_copy(
                            update={
                                "duration_ms": int((time.monotonic() - start) * 1000)
                            }
                        )

                yield encode_event(payload)

        except Exception as exc:
            logger.exception("adapt_stream: erro no stream LangGraph")
            yield encode_event(ErrorEvent(message=str(exc), code="STREAM_ERROR"))

        finally:
            yield encode_event(DoneEvent(thread_id=thread_id))

    return _gen()

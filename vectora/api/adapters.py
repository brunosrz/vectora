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

from vectora.api.node_labels import get_node_label
from vectora.api.schemas import (
    DoneEvent,
    ErrorEvent,
    HITLEvent,
    NodeEvent,
    StreamChatEventPayload,
    ThinkingEvent,
    TokenEvent,
    ToolCallEvent,
    ToolResultEvent,
    UIMetricsEvent,
    encode_event,
)

logger = logging.getLogger(__name__)

# Cache de metadados de tool: nome → dict com render_hint, category, destructive, icon.
# Populado lazily para evitar importar ALL_TOOLS no startup.
_tool_meta_cache: dict[str, dict] = {}

_DEFAULT_META = {
    "render_hint": "json",
    "category": "general",
    "destructive": False,
    "icon": "tool",
}


def _get_tool_meta(tool_name: str) -> dict:
    """Retorna metadados de UI da tool (render_hint, category, destructive, icon)."""
    if not _tool_meta_cache:
        try:
            from vectora.nodes.tools import ALL_TOOLS

            for t in ALL_TOOLS:
                meta = getattr(t, "extras", None) or getattr(t, "metadata", None) or {}
                _tool_meta_cache[t.name] = {
                    "render_hint": meta.get("render_hint", "json"),
                    "category": meta.get("category", "general"),
                    "destructive": bool(meta.get("destructive", False)),
                    "icon": meta.get("icon", "tool"),
                }
        except Exception:
            pass
    return _tool_meta_cache.get(tool_name, _DEFAULT_META)


# ---------------------------------------------------------------------------
# Nós que emitem tokens user-facing (sub-grafos podem ter nomes diferentes)
# ---------------------------------------------------------------------------
_STREAMING_NODES = {
    "invoke_llm",
    "search_agent",
    "coder_agent",
    "rag_agent",
}

# Nós cuja saída do LLM é JSON estruturado (Pydantic) — não é prosa pro usuário.
# Os tokens emitidos durante a decisão estruturada são filtrados; o conteúdo final
# (campo `response` da decisão "respond") é emitido como TokenEvent único no
# `on_chain_end` do nó orchestrator (ver adapt_stream).
_STRUCTURED_OUTPUT_NODES = {"orchestrator"}


def _extract_orchestrator_response(event: dict[str, Any]) -> str | None:
    """Extrai o texto da resposta direta do orchestrator (action="respond").

    O orchestrator retorna ``Command(goto=END, update={"messages": [AIMessage(content=...)]})``.
    No evento ``on_chain_end`` do nó, o ``data.output`` contém esse update.
    Quando o orchestrator delega (não responde direto), não há AIMessage com
    conteúdo de texto — retorna None.
    """
    data = event.get("data", {}) or {}
    output = data.get("output", None)
    if output is None:
        return None

    # output pode ser Command, dict, ou objeto com atributo .update
    messages: list | None = None
    if isinstance(output, dict):
        # Estado dict — `messages` em raiz, ou em "update"
        messages = output.get("messages")
        if messages is None and isinstance(output.get("update"), dict):
            messages = output["update"].get("messages")
    elif hasattr(output, "update"):
        upd = getattr(output, "update", None)
        if isinstance(upd, dict):
            messages = upd.get("messages")

    if not messages:
        return None

    last = messages[-1]
    content = getattr(last, "content", None)
    if content is None and isinstance(last, dict):
        content = last.get("content")
    if not content or not isinstance(content, str):
        return None
    return content


def _extract_orchestrator_thinking(event: dict[str, Any]) -> dict[str, Any] | None:
    """Extrai dados de raciocínio do orchestrator do evento on_chain_end.

    O nó orchestrator grava um dict `thinking` no state update com:
      reason, action, delegate_to, task_query

    Retorna None se não for evento do orchestrator ou se não houver thinking.
    """
    if event.get("name") != "orchestrator":
        return None
    data = event.get("data", {}) or {}
    output = data.get("output")
    if output is None:
        return None

    # output pode ser dict (estado direto) ou Command(update={...})
    candidate: dict | None = None
    if isinstance(output, dict):
        candidate = output
    elif hasattr(output, "update") and isinstance(
        getattr(output, "update", None), dict
    ):
        candidate = output.update  # type: ignore[union-attr]

    if candidate is None:
        return None

    thinking = candidate.get("thinking")
    if isinstance(thinking, dict) and "reason" in thinking:
        return thinking
    return None


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
        # Filtrar saída de nós com structured output (Pydantic) — esses tokens
        # são JSON cru da decisão estruturada, não user-facing.
        md = event.get("metadata", {}) or {}
        lg_node = md.get("langgraph_node", "")
        if lg_node in _STRUCTURED_OUTPUT_NODES:
            return None

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
        meta = _get_tool_meta(name)
        return ToolCallEvent(
            tool_name=name,
            tool_call_id=call_id,
            args_json=args_json,
            render_hint=meta["render_hint"],
            category=meta["category"],
            destructive=meta["destructive"],
            icon=meta["icon"],
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
        return NodeEvent(node=name, status="started", node_label=get_node_label(name))

    if kind == "on_chain_end" and name not in ("", "LangGraph"):
        return NodeEvent(node=name, status="finished", node_label=get_node_label(name))

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

                # Extrai data uma vez para o bloco HITL + orchestrator abaixo
                data = event.get("data", {})

                # ── HITL: interrupt() chamado em algum nó ────────────────────
                # Quando hitl_check chama interrupt(payload), o LangGraph emite
                # um on_chain_stream com "__interrupt__" no chunk. Detectamos
                # esse sentinel e traduzimos para HITLEvent antes do DoneEvent.
                if kind == "on_chain_stream":
                    chunk = data.get("chunk", {})
                    if isinstance(chunk, dict) and "__interrupt__" in chunk:
                        raw_interrupts = chunk["__interrupt__"]
                        for intr in raw_interrupts:
                            intr_val = getattr(intr, "value", None)
                            if not isinstance(intr_val, list) or not intr_val:
                                continue
                            first = intr_val[0]
                            yield encode_event(
                                HITLEvent(
                                    tool_name=first.get("name", "unknown"),
                                    args_json=json.dumps(first.get("args", {})),
                                    interrupt_id=first.get("id", ""),
                                )
                            )
                        # Stream encerra aqui — cliente exibirá o painel HITL
                        # e chamará ResumeChat para continuar.
                        return

                # Caso especial: orchestrator decidiu "respond" — extrai a
                # `response` do AIMessage emitido pelo Command e envia como
                # TokenEvent único (já que os tokens do LLM foram filtrados
                # acima por serem JSON estruturado).
                if kind == "on_chain_end" and name == "orchestrator":
                    thinking = _extract_orchestrator_thinking(event)
                    if thinking:
                        yield encode_event(
                            ThinkingEvent(
                                reason=thinking["reason"],
                                action=thinking.get("action", "respond"),
                                delegate_to=thinking.get("delegate_to"),
                                task_query=thinking.get("task_query"),
                            )
                        )
                    response_text = _extract_orchestrator_response(event)
                    if response_text:
                        yield encode_event(
                            TokenEvent(content=response_text, node="orchestrator")
                        )

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

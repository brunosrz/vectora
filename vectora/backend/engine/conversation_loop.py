"""``run_conversation`` — loop de conversa nativo (Sprint 14, Workstream 5).
Substitui o ``StateGraph`` do LangGraph por um loop ``while`` imperativo,
estilo Hermes Agent: a cada volta relê o histórico da persistência (nunca
mantém estado só em memória — reload/resume funcionam por reconstrução,
mesmo invariante de ``SessionStore``), chama o chat client em streaming,
acumula os fragmentos, executa as tool calls resultantes, e repete.

``max_iterations`` substitui ``recursion_limit`` (o teto de super-steps que
o LangGraph aplicava); estourar emite ``stopped_reason="max_iterations"`` —
mesmo código que o frontend já trata hoje via `ErrorSignal(code=
"RECURSION_LIMIT")` no adapter atual (Workstream 6 mapeia esse resultado
pro evento SSE equivalente).

HITL (Workstream 7) entra por injeção: ``should_require_approval`` é uma
função pura opcional — se fornecida e disparar pra qualquer tool call do
lote, o loop pausa ali (``stopped_reason="interrupted"``) como controle
normal, sem executar nenhuma tool do lote. Sem a função (workstream ainda
não commitado), o loop nunca pausa. `interrupt_id` é gerado aqui
(``uuid4``) — a persistência síncrona antes da espera (sobrevivência a
restart) é o que o Workstream 7 adiciona por cima, não uma mudança neste
loop.

Eventos emitidos via ``on_event`` (Workstream 6, ``backend/engine/
stream_events.py``) são os mesmos tipos que ``sse_adapter.py`` serializa
pro contrato SSE que o frontend já consome — o loop não sabe nada sobre
SSE, só produz o vocabulário nativo.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from backend.engine.stream_events import (
    HitlRequested,
    MessageBreak,
    MessageChunk,
    ToolResult,
)
from backend.engine.tool_batch import execute_tool_batch
from backend.vtypes.message import ContentBlock, MessageRole, ToolCall, VMessage

if TYPE_CHECKING:
    from collections.abc import Callable

    from backend.engine.stream_events import EventSink
    from backend.llm.base import ChatClient
    from backend.persistence.native.session_store import SessionStore
    from backend.tools.context import ToolContext
    from backend.tools.registry import ToolRegistry


@dataclass(slots=True)
class LoopConfig:
    """Configuração de uma execução do loop — um objeto por turno."""

    max_iterations: int = 50
    temperature: float | None = None
    max_tokens: int | None = None


@dataclass(slots=True)
class LoopResult:
    """Resultado de uma chamada a `run_conversation`."""

    stopped_reason: str
    """`"stop"` | `"max_iterations"` | `"interrupted"`."""
    final_message: VMessage | None = None


async def _noop_event(_event: object) -> None:
    return None


def _resolve_tool_calls(acumulado: dict[int, dict[str, Any]]) -> list[ToolCall]:
    """Monta `ToolCall`s completas a partir dos fragmentos acumulados por
    `index` — `arguments` inválido não derruba o turno, vira `_parse_error`
    (mesmo padrão já usado nos 5 chat clients nativos)."""
    chamadas: list[ToolCall] = []
    for indice in sorted(acumulado):
        item = acumulado[indice]
        args_texto = item["args_fragment"] or "{}"
        try:
            args = json.loads(args_texto)
        except json.JSONDecodeError:
            args = {"_parse_error": args_texto}
        if not isinstance(args, dict):
            args = {"_parse_error": args_texto}
        chamadas.append(
            ToolCall(id=item["id"] or "", name=item["name"] or "", args=args)
        )
    return chamadas


async def run_conversation(
    *,
    session_store: SessionStore,
    chat_client: ChatClient,
    tool_registry: ToolRegistry,
    ctx: ToolContext,
    thread_id: str,
    config: LoopConfig,
    on_event: EventSink | None = None,
    should_require_approval: Callable[[str, ToolContext, dict[str, Any]], bool]
    | None = None,
) -> LoopResult:
    emit = on_event or _noop_event
    tools = tool_registry.all()
    parent_id = await session_store.get_branch_head_id(thread_id)

    for _iteracao in range(config.max_iterations):
        historico = await session_store.get_history(thread_id)

        partes_texto: list[str] = []
        tool_call_chunks_por_indice: dict[int, dict[str, Any]] = {}

        async for chunk in chat_client.astream(
            historico,
            tools=tools,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        ):
            if chunk.delta_text:
                partes_texto.append(chunk.delta_text)
                await emit(MessageChunk(content=chunk.delta_text))

            for tc_chunk in chunk.tool_call_chunks:
                acumulado = tool_call_chunks_por_indice.setdefault(
                    tc_chunk.index, {"id": None, "name": None, "args_fragment": ""}
                )
                if tc_chunk.id:
                    acumulado["id"] = tc_chunk.id
                if tc_chunk.name:
                    acumulado["name"] = tc_chunk.name
                acumulado["args_fragment"] += tc_chunk.args_fragment

            # `usage` não tem evento SSE dedicado — rastreio de custo
            # (Workstream 10) lê `VMessageChunk.usage` diretamente do
            # stream do chat client, não via `on_event`.

        texto_final = "".join(partes_texto)
        tool_calls = _resolve_tool_calls(tool_call_chunks_por_indice)

        assistant_msg = VMessage(
            role=MessageRole.ASSISTANT,
            content=[ContentBlock(kind="text", text=texto_final)]
            if texto_final
            else [],
            tool_calls=tool_calls,
            finish_reason="tool_calls" if tool_calls else "stop",
        )
        parent_id = await session_store.append_message(
            thread_id, assistant_msg, parent_message_id=parent_id
        )
        await emit(MessageBreak())

        if not tool_calls:
            return LoopResult(stopped_reason="stop", final_message=assistant_msg)

        if should_require_approval is not None:
            pendente = next(
                (
                    tc
                    for tc in tool_calls
                    if should_require_approval(tc.name, ctx, tc.args)
                ),
                None,
            )
            if pendente is not None:
                await emit(
                    HitlRequested(
                        tool_name=pendente.name,
                        args_json=json.dumps(pendente.args, ensure_ascii=False),
                        interrupt_id=str(uuid4()),
                    )
                )
                return LoopResult(
                    stopped_reason="interrupted", final_message=assistant_msg
                )

        resultados = await execute_tool_batch(
            tool_calls, tool_registry=tool_registry, ctx=ctx
        )
        for resultado in resultados:
            parent_id = await session_store.append_message(
                thread_id, resultado, parent_message_id=parent_id
            )
            await emit(
                ToolResult(
                    tool_call_id=resultado.tool_call_id or "",
                    content_json=resultado.text(),
                    is_error=resultado.is_error,
                )
            )

    return LoopResult(stopped_reason="max_iterations")

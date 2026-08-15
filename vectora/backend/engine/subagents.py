"""Delegação de subagentes nativa. Cada subagente é uma instância nova do
motor nativo (``run_conversation``) rodando com seu próprio ``SessionStore``
thread, tools restritas ao ``SubagentSpec``, e prompt de sistema próprio —
``asyncio.Task``, nunca thread OS (CLAUDE.md regra 10).

``SubagentSpec.tools`` já são ``ToolSpec`` do registry nativo — não os
``@tool`` do LangChain que ``backend/agents/souls.py`` (catálogo real em
produção, ``SOUL_CATALOG``) ainda usa. Esse arquivo continua sendo a fonte
de verdade em produção até a migração das ~152 tools pro registry nativo
acontecer e o dispatch cortar pro motor novo — este módulo entrega o
MECANISMO de delegação nativo, testável com qualquer ``ToolRegistry``,
coexistindo sem depender de um catálogo ainda inexistente.

Sub-thread_id = ``f"{parent_thread_id}:{spec.name}:{uuid4()}"`` com
``parent_thread_id`` gravado em ``SessionStore.create_session`` — dá
rastreabilidade completa (qualquer subagente sabe de qual conversa/task
veio).

HITL dentro do subagente: ``should_require_approval`` (``backend/engine/
hitl.py``) é passado direto pro `run_conversation` do subagente — chamado
IDENTICAMENTE ao do agente principal, porque é código importado, não
estado injetado por instância de middleware. Resolve o gap que o
deepagents tinha (subagente herdava `interrupt_on` do topo do grafo, nunca
o `middleware=` custom do pai) sem precisar de nenhum truque de propagação.

Liveness ativa (``LivenessConfig``): heartbeat baseado em progresso real
(qualquer evento emitido pelo `run_conversation` do subagente — token,
tool_call, etc.), não só existência do processo. Sem atividade por
``heartbeat_interval_s * max_stalled_heartbeats`` segundos, o watchdog
cancela a `asyncio.Task` do subagente — nunca deixa um loop preso rodando
pra sempre. Pausa legítima em HITL não conta como "travado": o
`run_conversation` retorna (task termina) ao pausar, então o watchdog
nunca chega a competir com uma delegação esperando aprovação de verdade.

Escopo RBAC do subagente (``_tools_outside_user_scope``): as tools
do ``SubagentSpec`` nunca podem exceder o que ``tool_policy.
effective_disabled(ctx.user_id)`` permite pro usuário/sessão que está
delegando — mesmo filtro que ``agent_factory._subagent_specs()`` já aplica
no catálogo LangGraph em produção (kill-switch global + ABAC por usuário),
replicado aqui pro motor nativo não abrir uma segunda porta sem esse
filtro quando o corte de dispatch acontecer.
"""

from __future__ import annotations

import asyncio
import contextlib
import time
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from backend.engine.conversation_loop import LoopConfig, run_conversation
from backend.engine.stream_events import SubagentOutput
from backend.rbac import tool_policy
from backend.tools.registry import ToolRegistry
from backend.vtypes.message import MessageRole, text_message

if TYPE_CHECKING:
    from collections.abc import Callable

    from backend.engine.guardrails import TurnBudget
    from backend.engine.stream_events import EventSink
    from backend.llm.base import ChatClient
    from backend.persistence.native.session_store import SessionStore
    from backend.tools.context import ToolContext
    from backend.tools.registry import ToolSpec
    from backend.vtypes.message import VMessage


@dataclass(slots=True)
class SubagentSpec:
    """Spec nativa de subagente — mesmo papel de `Soul`
    (`backend/agents/souls.py`), tools já resolvidas como `ToolSpec`."""

    name: str
    description: str
    system_prompt: str
    tools: list[ToolSpec]


@dataclass(slots=True)
class LivenessConfig:
    """Teto de inatividade antes do watchdog cancelar o subagente.

    O watchdog só existe quando `run_subagent` recebe `liveness=` — sem
    isso (default), o subagente roda até completar sem nenhum teto de
    tempo, comportamento inalterado."""

    heartbeat_interval_s: float = 30.0
    max_stalled_heartbeats: int = 3


def _sub_thread_id(parent_thread_id: str, subagent_name: str) -> str:
    return f"{parent_thread_id}:{subagent_name}:{uuid4()}"


def _tools_outside_user_scope(tools: list[ToolSpec], user_id: str | None) -> list[str]:
    """Nomes de tool do `SubagentSpec` que o usuário não teria permissão de
    usar diretamente (kill-switch global ou ABAC por usuário) — mesmo
    filtro que `agent_factory._subagent_specs()` já aplica em produção."""
    disabled = tool_policy.effective_disabled(user_id)
    return [t.name for t in tools if t.name in disabled]


async def _watch_liveness(
    task: asyncio.Task[Any],
    liveness: LivenessConfig,
    last_activity: list[float],
) -> None:
    """Corre em paralelo a `task` — dispara (retorna) quando não há
    atividade registrada em `last_activity[0]` por tempo suficiente. Só
    checa enquanto `task` ainda está rodando; termina sozinho se `task`
    concluir primeiro (nada a cancelar)."""
    limite = liveness.heartbeat_interval_s * liveness.max_stalled_heartbeats
    while not task.done():
        await asyncio.sleep(liveness.heartbeat_interval_s)
        if task.done():
            return
        if time.monotonic() - last_activity[0] >= limite:
            return


async def run_subagent(
    spec: SubagentSpec,
    prompt: str,
    *,
    session_store: SessionStore,
    chat_client: ChatClient,
    ctx: ToolContext,
    parent_thread_id: str,
    config: LoopConfig | None = None,
    on_event: EventSink | None = None,
    should_require_approval: Callable[
        [str, ToolContext, dict[str, Any], list[VMessage]], bool
    ]
    | None = None,
    turn_budget: TurnBudget | None = None,
    liveness: LivenessConfig | None = None,
) -> str:
    """Roda `spec` até completar (ou pausar em HITL) e devolve o texto
    final — instância nova e isolada do motor, sessão própria com
    `parent_thread_id` gravado (rastreabilidade), sem herdar o histórico do
    chamador.

    `turn_budget`, quando fornecido, é o mesmo objeto do turno do agente
    pai (`backend/engine/guardrails.py::TurnBudget`) — o spawn é registrado
    contra o teto `max_subagent_spawns_per_turn` do turno pai antes de
    qualquer sessão ser criada; teto excedido recusa o spawn sem gastar
    nenhum recurso.

    `liveness`, quando fornecido, ativa o watchdog de inatividade — sem
    progresso (nenhum evento emitido pelo subagente) por
    `heartbeat_interval_s * max_stalled_heartbeats` segundos, a task é
    cancelada e o resultado vira `status="cancelled"`. Sem `liveness`
    (default), o subagente roda até completar normalmente, sem watchdog.

    Erro/borda: `spec.tools` pedindo tool fora do escopo RBAC do usuário
    (`ctx.user_id`, via `backend.rbac.tool_policy.effective_disabled`) é
    rejeitado antes de qualquer sessão ser criada — erro tipado, nenhuma
    chamada ao chat client."""
    fora_do_escopo = _tools_outside_user_scope(spec.tools, ctx.user_id)
    if fora_do_escopo:
        return (
            f"Error: subagente '{spec.name}' pede tool(s) fora do escopo "
            f"RBAC do usuário atual: {', '.join(sorted(fora_do_escopo))}."
        )

    if turn_budget is not None:
        estourado = turn_budget.record_subagent_spawn()
        if estourado is not None:
            return (
                f"Error: teto de guardrail do turno excedido ({estourado}) — "
                f"subagente '{spec.name}' não foi disparado."
            )

    thread_id = _sub_thread_id(parent_thread_id, spec.name)
    await session_store.create_session(
        thread_id,
        user_id=ctx.user_id,
        workspace_id=ctx.workspace_id or None,
        parent_thread_id=parent_thread_id,
        mode="subagent",
        permission_mode=ctx.permission_mode,
    )

    system_id = await session_store.append_message(
        thread_id, text_message(MessageRole.SYSTEM, spec.system_prompt)
    )
    await session_store.append_message(
        thread_id,
        text_message(MessageRole.USER, prompt),
        parent_message_id=system_id,
    )

    sub_registry = ToolRegistry()
    for tool_spec in spec.tools:
        sub_registry.register(tool_spec)

    sub_ctx = replace(ctx, thread_id=thread_id)

    if on_event is not None:
        await on_event(
            SubagentOutput(
                subagent_type=spec.name, description=spec.description, status="running"
            )
        )

    last_activity = [time.monotonic()]

    async def _on_event_com_liveness(event: Any) -> None:
        last_activity[0] = time.monotonic()
        if on_event is not None:
            await on_event(event)

    conversation_task: asyncio.Task[Any] = asyncio.create_task(
        run_conversation(
            session_store=session_store,
            chat_client=chat_client,
            tool_registry=sub_registry,
            ctx=sub_ctx,
            thread_id=thread_id,
            config=config or LoopConfig(),
            on_event=_on_event_com_liveness if liveness is not None else on_event,
            should_require_approval=should_require_approval,
        )
    )

    if liveness is not None:
        watchdog_task = asyncio.create_task(
            _watch_liveness(conversation_task, liveness, last_activity)
        )
        await asyncio.wait(
            {conversation_task, watchdog_task}, return_when=asyncio.FIRST_COMPLETED
        )
        if not conversation_task.done():
            conversation_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await conversation_task
            texto_cancelado = (
                f"Subagente '{spec.name}' cancelado por inatividade — sem "
                f"progresso por "
                f"{liveness.heartbeat_interval_s * liveness.max_stalled_heartbeats:.0f}s."
            )
            if on_event is not None:
                await on_event(
                    SubagentOutput(
                        subagent_type=spec.name,
                        status="cancelled",
                        content=texto_cancelado,
                    )
                )
            return texto_cancelado
        watchdog_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await watchdog_task

    resultado = await conversation_task

    texto = resultado.final_message.text() if resultado.final_message else ""

    if resultado.stopped_reason == "stop":
        status = "complete"
    elif resultado.stopped_reason == "interrupted":
        # Ainda pausado esperando aprovação — nem sucesso nem erro. Não
        # emite evento de conclusão: o subagente segue "running" até
        # alguém retomar (fora do escopo deste workstream — a UI vê a
        # pendência via o mesmo pending_approvals do agente principal).
        status = "running"
    else:
        status = "error"

    if status != "running" and on_event is not None:
        await on_event(
            SubagentOutput(subagent_type=spec.name, status=status, content=texto)
        )

    return texto


def spawn_subagent_background(
    spec: SubagentSpec, prompt: str, **kwargs: Any
) -> asyncio.Task[str]:
    """Dispara `run_subagent` em segundo plano via `asyncio.create_task` —
    nunca thread OS (CLAUDE.md regra 10). Devolve a `asyncio.Task[str]` pra
    quem chamou decidir se/quando esperar (ex.: `await` direto pra
    delegação síncrona, ou nunca esperar pra fire-and-forget real)."""
    return asyncio.create_task(run_subagent(spec, prompt, **kwargs))

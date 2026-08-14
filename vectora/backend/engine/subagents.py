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
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from backend.engine.conversation_loop import LoopConfig, run_conversation
from backend.engine.stream_events import SubagentOutput
from backend.tools.registry import ToolRegistry
from backend.vtypes.message import MessageRole, text_message

if TYPE_CHECKING:
    from collections.abc import Callable

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


def _sub_thread_id(parent_thread_id: str, subagent_name: str) -> str:
    return f"{parent_thread_id}:{subagent_name}:{uuid4()}"


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
) -> str:
    """Roda `spec` até completar (ou pausar em HITL) e devolve o texto
    final — instância nova e isolada do motor, sessão própria com
    `parent_thread_id` gravado (rastreabilidade), sem herdar o histórico do
    chamador."""
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

    resultado = await run_conversation(
        session_store=session_store,
        chat_client=chat_client,
        tool_registry=sub_registry,
        ctx=sub_ctx,
        thread_id=thread_id,
        config=config or LoopConfig(),
        on_event=on_event,
        should_require_approval=should_require_approval,
    )

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

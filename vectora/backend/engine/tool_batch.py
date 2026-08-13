"""``execute_tool_batch`` — paralelização de tool calls do mesmo turno
(Sprint 14, Workstream 5). Substitui ``backend/nodes/parallel_tools.py::
ParallelToolNode(ToolNode)``.

Regra de segurança de paralelismo: tool calls não-destrutivas do mesmo lote
rodam via ``asyncio.gather`` (mesma granularidade que ``ToolExtras.
destructive`` já expõe); qualquer tool destrutiva no lote força execução
sequencial do lote inteiro — evita duas escritas concorrentes na mesma
sessão/arquivo/recurso externo por causa de paralelismo, mesmo quando só
uma das chamadas é a arriscada.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from backend.vtypes.message import ContentBlock, MessageRole, VMessage

if TYPE_CHECKING:
    from backend.tools.context import ToolContext
    from backend.tools.registry import ToolRegistry
    from backend.vtypes.message import ToolCall


async def _run_one(
    tool_call: ToolCall, *, tool_registry: ToolRegistry, ctx: ToolContext
) -> VMessage:
    spec = tool_registry.get(tool_call.name)
    if spec is None:
        texto = f"Error: tool '{tool_call.name}' não encontrada no registry"
        is_error = True
    else:
        texto = await spec.ainvoke(tool_call.args, ctx)
        is_error = texto.startswith("Error:")
    return VMessage(
        role=MessageRole.TOOL,
        content=[ContentBlock(kind="text", text=texto)],
        tool_call_id=tool_call.id,
        name=tool_call.name,
        is_error=is_error,
    )


async def execute_tool_batch(
    tool_calls: list[ToolCall], *, tool_registry: ToolRegistry, ctx: ToolContext
) -> list[VMessage]:
    """Executa todas as `tool_calls` do turno, na ordem em que aparecem no
    resultado — paralelo se nenhuma é destrutiva, sequencial (mas ainda
    assim todas executadas) se qualquer uma é."""
    algum_destrutivo = any(
        (spec := tool_registry.get(tc.name)) is not None and spec.extras.destructive
        for tc in tool_calls
    )

    if algum_destrutivo:
        return [
            await _run_one(tc, tool_registry=tool_registry, ctx=ctx)
            for tc in tool_calls
        ]

    return list(
        await asyncio.gather(
            *(_run_one(tc, tool_registry=tool_registry, ctx=ctx) for tc in tool_calls)
        )
    )

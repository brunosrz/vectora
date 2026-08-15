"""Ponte temporária: expõe um `ToolSpec` do registry nativo
(`backend/tools/registry.py`) como uma `StructuredTool` do LangChain.

Existe só pra permitir migrar tools pro formato `@vtool` **uma de cada
vez**, sem exigir um big-bang simultâneo com o corte de dispatch — o
dispatch de produção hoje (`agent_factory.py`/`create_deep_agent`) só sabe
consumir `BaseTool`. Cada tool migrada é registrada nos dois lugares: o
`TOOL_REGISTRY` nativo (fonte de verdade, `ToolSpec`) e, via esta ponte,
como `BaseTool` na lista que `backend/tools/__init__.py`/`backend/nodes/
tools.py` montam pro grafo LangGraph atual.

Removida por completo quando o corte de dispatch (motor nativo assume
`stream_chat`/`resume_chat`) acontecer — nesse ponto a lista de tools do
grafo LangGraph deixa de existir, e todo consumidor lê direto do
`TOOL_REGISTRY`.
"""

from __future__ import annotations

from typing import Annotated, Any

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg, StructuredTool

from backend.vtypes.context import ctx_from_config

from .registry import ToolSpec


def as_langchain_tool(spec: ToolSpec) -> StructuredTool:
    """Envolve `spec` numa `StructuredTool` — schema/nome/descrição vêm do
    `ToolSpec` (fonte única), a chamada real delega pra `spec.ainvoke`
    depois de converter o `RunnableConfig` injetado pelo LangGraph num
    `ToolContext` (mesma conversão que `ctx_from_config` já faz pra código
    legado)."""

    async def _run(
        config: Annotated[RunnableConfig, InjectedToolArg] = None,  # ty: ignore[invalid-parameter-default]
        **kwargs: Any,
    ) -> str:
        ctx = ctx_from_config(config)  # ty: ignore[invalid-argument-type]
        return await spec.ainvoke(kwargs, ctx)

    _run.__name__ = spec.name
    _run.__doc__ = spec.description

    return StructuredTool.from_function(
        coroutine=_run,
        name=spec.name,
        description=spec.description,
        args_schema=spec.args_model,
        extras={
            "render_hint": spec.extras.render_hint,
            "category": spec.extras.category,
            "destructive": spec.extras.destructive,
            "icon": spec.extras.icon,
            "invalidates": spec.extras.invalidates,
        },
    )

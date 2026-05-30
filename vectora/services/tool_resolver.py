"""Resolução do toolset por usuário — Bloco S (S4).

Combina as tools built-in permitidas (consultando ``tool_policy``) com as tools
dos servidores MCP do usuário (``plugins.get_user_mcp_tools``). Usado pelos
agents (para bindar no LLM) e pelo ToolNode dinâmico (para executar), a cada
request, a partir do ``user_id`` do RunnableConfig.

Sem ``user_id`` (CLI/root local) → ALL_TOOLS direto, sem consulta de política
nem MCP — preserva o comportamento local.
"""

from __future__ import annotations

import logging

from vectora.nodes.tools import ALL_TOOLS
from vectora.services import tool_policy
from vectora.services.plugins import get_user_mcp_tools

logger = logging.getLogger(__name__)


async def resolve_tools(user_id: str | None) -> list:
    """Retorna o toolset efetivo do usuário (built-ins permitidas + MCP)."""
    if not user_id or user_id == "local":
        return list(ALL_TOOLS)

    builtins = [t for t in ALL_TOOLS if tool_policy.is_allowed(user_id, t.name)]

    try:
        mcp_tools = await get_user_mcp_tools(user_id)
    except Exception:
        logger.warning("tool_resolver: MCP indisponível para %s", user_id)
        mcp_tools = []

    return [*builtins, *mcp_tools]

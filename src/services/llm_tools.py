"""LLM bindado ao toolset do usuário — Bloco S (S6).

Os agents executores (coder, search) precisam que o LLM "veja" as tools que o
usuário pode usar (built-ins permitidas + tools dos MCP servers dele). Como o
toolset é idêntico entre os agents (a especialização vem do system prompt), um
único cache compartilhado por ``(user_id, versão)`` serve aos dois.

A versão combina a config MCP (``plugins.tools_version``) e a política de tools
(``tool_policy.policy_version``) — qualquer mudança invalida o bind sem reiniciar.
"""

from __future__ import annotations

import logging
from typing import Any

from src.services import tool_policy
from src.services.plugins import tools_version
from src.services.tool_resolver import resolve_tools
from src.services.utils import load_llm

logger = logging.getLogger(__name__)

#: cache: (user_id, mcp_version, policy_version) -> LLM bindado
_bound_cache: dict[tuple[str, int, int], Any] = {}


def user_id_from_config(config: Any) -> str | None:
    """Extrai o user_id do RunnableConfig (ou None em modo local/CLI)."""
    if isinstance(config, dict):
        configurable = config.get("configurable")
        if isinstance(configurable, dict):
            return configurable.get("user_id")
    return None


async def get_user_bound_llm(user_id: str | None) -> Any:
    """Retorna um LLM bindado ao toolset efetivo do usuário (cacheado)."""
    uid = user_id or "local"
    key = (uid, tools_version(uid), tool_policy.policy_version(uid))
    cached = _bound_cache.get(key)
    if cached is not None:
        return cached

    base = load_llm()
    if not hasattr(base, "bind_tools"):
        _bound_cache[key] = base
        return base

    tools = await resolve_tools(user_id)
    bound = base.bind_tools(tools)  # type: ignore[attr-defined]  # ty: ignore[call-non-callable]
    _bound_cache[key] = bound
    logger.debug("LLM bindado para %s com %d tools", uid, len(tools))
    return bound

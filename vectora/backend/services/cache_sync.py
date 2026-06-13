"""Sincronização de caches entre réplicas — Bloco G (G2).

Cada réplica mantém caches in-memory (L1): tools MCP resolvidas, LLM bindado,
política de tools e workspace ativo. Quando uma réplica muda algo, publica no
KV (Redis pub/sub em modo complete); as demais aplicam a mudança localmente.

Canais:
    vectora:tools      {"user_id", "version"}  → plugins + llm_tools
    vectora:policy     {"user_id", "version"}  → tool_policy + llm_tools
    vectora:ws-active  {"user_id", "workspace_id"} → workspace_registry

Em modo lite (MemoryKV) o publish entrega no próprio processo — inofensivo.
"""

from __future__ import annotations

import json
import logging

from backend.services.kv import get_kv

logger = logging.getLogger(__name__)

CHANNEL_TOOLS = "vectora:tools"
CHANNEL_POLICY = "vectora:policy"
CHANNEL_WS_ACTIVE = "vectora:ws-active"


def _parse(payload: str) -> dict:
    try:
        data = json.loads(payload)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def _on_tools_changed(payload: str) -> None:
    data = _parse(payload)
    user_id = str(data.get("user_id", ""))
    version = int(data.get("version", 0))
    if not user_id:
        return
    from backend.services import plugins

    plugins.apply_remote_version(user_id, version)


def _on_policy_changed(payload: str) -> None:
    data = _parse(payload)
    user_id = str(data.get("user_id", ""))
    version = int(data.get("version", 0))
    if not user_id:
        return
    from backend.services import tool_policy

    tool_policy.apply_remote_version(user_id, version)


def _on_ws_active_changed(payload: str) -> None:
    data = _parse(payload)
    user_id = str(data.get("user_id", ""))
    workspace_id = str(data.get("workspace_id", ""))
    if not user_id or not workspace_id:
        return
    from backend.services.workspace import workspace_registry

    workspace_registry.apply_remote_active(workspace_id, user_id)


async def start_cache_sync() -> None:
    """Registra os subscribers e inicia o reader (chamado no lifespan)."""
    kv = get_kv()
    kv.subscribe(CHANNEL_TOOLS, _on_tools_changed)
    kv.subscribe(CHANNEL_POLICY, _on_policy_changed)
    kv.subscribe(CHANNEL_WS_ACTIVE, _on_ws_active_changed)
    await kv.start()
    logger.info("cache_sync: subscribers registrados (%s)", type(kv).__name__)


async def stop_cache_sync() -> None:
    await get_kv().close()

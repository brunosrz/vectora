"""Memory tools: persistência de memórias entre sessões.

As memórias são isoladas por sessão (D3): cada thread_id recebe seu próprio
namespace, evitando poluição de contexto entre projetos/conversas.
"""

import json
import logging
from typing import Any

from langchain.tools import tool
from langchain_core.runnables import RunnableConfig

logger = logging.getLogger(__name__)


def _user_id_from_config(config: RunnableConfig | None) -> str:
    """Deriva user_id a partir do thread_id da sessão LangGraph.

    Retorna 'session_<thread_id>' para isolamento por sessão (D3).
    Fallback para 'default_session' quando config não está disponível
    (ex: chamadas diretas fora de um grafo LangGraph).
    """
    if config is None:
        return "default_session"
    thread_id = (config.get("configurable") or {}).get("thread_id")
    return f"session_{thread_id}" if thread_id else "default_session"


@tool
async def save_memory(
    key: str,
    content: str,
    config: RunnableConfig,
    metadata: dict[str, Any] | None = None,
    ttl_days: int | None = None,
) -> str:
    """Salva uma memória persistente para uso em futuras conversas da mesma sessão.

    As memórias são isoladas por sessão (thread_id) para evitar poluição entre
    projetos distintos. São armazenadas no SQLite e recuperadas automaticamente
    nas próximas interações da mesma sessão.

    Args:
        key: Chave única da memória (ex: 'user_preferences', 'project_context')
        content: Conteúdo da memória (string com informações a recordar)
        config: Injetado automaticamente pelo LangGraph com thread_id da sessão
        metadata: Metadados adicionais
        ttl_days: Dias até expiração automática (None = nunca expira)

    Returns:
        JSON com status saved/failed
    """
    try:
        from vectora.services.memory import get_memory_store

        user_id = _user_id_from_config(config)
        memory_store = await get_memory_store()
        memory_id = await memory_store.save(
            user_id=user_id,
            key=key,
            content=content,
            metadata=metadata,
            ttl_days=ttl_days,
        )

        logger.info(
            "memory_saved",
            extra={"key": key, "memory_id": memory_id, "ttl_days": ttl_days},
        )

        return json.dumps(
            {
                "status": "saved",
                "memory_id": memory_id,
                "key": key,
                "expires_in_days": ttl_days,
            }
        )

    except Exception as e:
        logger.exception("save_memory_failed", extra={"key": key})
        return json.dumps({"status": "failed", "error": str(e), "key": key})


@tool
async def get_memory(config: RunnableConfig, key: str | None = None) -> str:
    """Recupera memórias persistentes salvas na sessão atual.

    Retorna apenas memórias do namespace desta sessão (thread_id), garantindo
    isolamento entre projetos/conversas diferentes.

    Args:
        config: Injetado automaticamente pelo LangGraph com thread_id da sessão
        key: Chave da memória específica. Se None, retorna todas as memórias.

    Returns:
        JSON com conteúdo da memória ou lista de memórias
    """
    try:
        from vectora.services.memory import get_memory_store

        user_id = _user_id_from_config(config)
        memory_store = await get_memory_store()

        if key is not None:
            memory = await memory_store.get(user_id, key)
            if memory is None:
                logger.warning("memory_not_found", extra={"key": key})
                return json.dumps({"status": "not_found", "key": key})

            logger.debug("memory_retrieved", extra={"key": key})
            return json.dumps(
                {
                    "status": "found",
                    "key": key,
                    "content": memory["content"],
                    "metadata": memory["metadata"],
                    "updated_at": memory["updated_at"],
                }
            )

        all_memories = await memory_store.get_all(user_id)
        logger.debug("all_memories_retrieved", extra={"count": len(all_memories)})
        return json.dumps(
            {
                "status": "success",
                "count": len(all_memories),
                "memories": [
                    {
                        "key": m["key"],
                        "content": m["content"],
                        "metadata": m["metadata"],
                        "updated_at": m["updated_at"],
                    }
                    for m in all_memories
                ],
            }
        )

    except Exception as e:
        logger.exception("get_memory_failed", extra={"key": key})
        return json.dumps({"status": "failed", "error": str(e)})


@tool
async def delete_memory(key: str, config: RunnableConfig) -> str:
    """Deleta uma memória persistente da sessão atual.

    Args:
        key: Chave da memória a deletar
        config: Injetado automaticamente pelo LangGraph com thread_id da sessão

    Returns:
        JSON com status deleted/not_found/failed
    """
    try:
        from vectora.services.memory import get_memory_store

        user_id = _user_id_from_config(config)
        memory_store = await get_memory_store()
        deleted = await memory_store.delete(user_id, key)

        if deleted:
            logger.info("memory_deleted", extra={"key": key})
            return json.dumps({"status": "deleted", "key": key})

        logger.warning("memory_not_found_for_deletion", extra={"key": key})
        return json.dumps({"status": "not_found", "key": key})

    except Exception as e:
        logger.exception("delete_memory_failed", extra={"key": key})
        return json.dumps({"status": "failed", "error": str(e), "key": key})

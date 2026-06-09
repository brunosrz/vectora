"""Memory tools: persistência de memórias entre sessões.

Migrado para LangGraph BaseStore (E.B-11): usa ``langgraph.config.get_store()``
para acessar o store injetado em ``create_deep_agent(store=...)``.

As memórias são isoladas por usuário no namespace ``("user", <user_id>, "memories")``,
garantindo isolamento entre usuários e compatibilidade com o StoreBackend do
CompositeBackend (E.B-8).
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from langchain.tools import tool
from langchain_core.runnables import RunnableConfig

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers de contexto
# ---------------------------------------------------------------------------


def _user_id_from_config(config: RunnableConfig | None) -> str:
    """Extrai user_id limpo do contexto LangGraph.

    Retorna o user_id em formato simples (sem prefixo) para uso como
    componente do namespace do store. Prioridade:
    1. user_id do configurable
    2. workspace_id (memórias seguem o projeto)
    3. thread_id (fallback por sessão)
    4. "local" (modo offline/anônimo)
    """
    if config is None:
        return "local"
    configurable = config.get("configurable") or {}
    user_id = configurable.get("user_id")
    if user_id:
        return str(user_id)
    workspace_id = configurable.get("workspace_id")
    if workspace_id:
        return f"workspace_{workspace_id}"
    thread_id = configurable.get("thread_id")
    return f"session_{thread_id}" if thread_id else "local"


def _memory_namespace(config: RunnableConfig | None) -> tuple[str, ...]:
    """Retorna o namespace do store para as memórias do usuário."""
    user_id = _user_id_from_config(config)
    return ("user", user_id, "memories")


def _get_store() -> Any:
    """Obtém o LangGraph store do contexto atual.

    Usa ``langgraph.config.get_store()`` que acessa o store via contextvar
    (injetado pelo harness deepagents quando ``store=`` é passado ao grafo).

    Raises:
        RuntimeError: Se chamado fora de um grafo LangGraph com store configurado.
    """
    from langgraph.config import get_store

    return get_store()


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@tool(
    extras={
        "render_hint": "json",
        "category": "memory",
        "destructive": False,
        "icon": "bookmark",
    }
)
async def save_memory(
    key: str,
    content: str,
    config: RunnableConfig,
    metadata: dict[str, Any] | None = None,
    ttl_days: int | None = None,
) -> str:
    """Salva uma memória persistente para uso em futuras conversas da mesma sessão.

    As memórias são isoladas por usuário para evitar poluição entre projetos distintos.
    Armazenadas no LangGraph BaseStore com suporte a busca semântica via Cohere
    quando configurado.

    Args:
        key: Chave única da memória (ex: 'user_preferences', 'project_context')
        content: Conteúdo da memória (string com informações a recordar)
        config: Injetado automaticamente pelo LangGraph com user_id/workspace_id
        metadata: Metadados adicionais
        ttl_days: Dias até expiração (informativo — store básico não garante TTL)

    Returns:
        JSON com status saved/failed
    """
    try:
        store = _get_store()
        ns = _memory_namespace(config)
        now = datetime.now(UTC).isoformat()

        value: dict[str, Any] = {
            "key": key,
            "content": content,
            "metadata": metadata or {},
            "updated_at": now,
        }
        if ttl_days is not None:
            value["ttl_days"] = ttl_days

        await store.aput(ns, key, value)

        logger.info(
            "memory_saved key=%s ns=%s ttl_days=%s",
            key,
            ns,
            ttl_days,
        )
        return json.dumps(
            {
                "status": "saved",
                "key": key,
                "namespace": list(ns),
                "expires_in_days": ttl_days,
            }
        )

    except Exception as exc:
        logger.exception("save_memory_failed key=%s", key)
        return json.dumps({"status": "failed", "error": str(exc), "key": key})


@tool(
    extras={
        "render_hint": "json",
        "category": "memory",
        "destructive": False,
        "icon": "bookmark-check",
    }
)
async def get_memory(config: RunnableConfig, key: str | None = None) -> str:
    """Recupera memórias persistentes salvas.

    Retorna apenas memórias do namespace do usuário/workspace atual.

    Args:
        config: Injetado automaticamente pelo LangGraph
        key: Chave específica. Se None, retorna todas as memórias do namespace.

    Returns:
        JSON com conteúdo da memória ou lista de memórias
    """
    try:
        store = _get_store()
        ns = _memory_namespace(config)

        if key is not None:
            item = await store.aget(ns, key)
            if item is None:
                logger.warning("memory_not_found key=%s ns=%s", key, ns)
                return json.dumps({"status": "not_found", "key": key})

            val = item.value
            logger.debug("memory_retrieved key=%s", key)
            return json.dumps(
                {
                    "status": "found",
                    "key": key,
                    "content": val.get("content", ""),
                    "metadata": val.get("metadata", {}),
                    "updated_at": val.get("updated_at"),
                }
            )

        # Sem key: lista todas as memórias do namespace
        items = await store.asearch(ns)
        memories = [
            {
                "key": item.key,
                "content": item.value.get("content", ""),
                "metadata": item.value.get("metadata", {}),
                "updated_at": item.value.get("updated_at"),
            }
            for item in items
        ]
        logger.debug("all_memories_retrieved count=%d ns=%s", len(memories), ns)
        return json.dumps(
            {
                "status": "success",
                "count": len(memories),
                "memories": memories,
            }
        )

    except Exception as exc:
        logger.exception("get_memory_failed key=%s", key)
        return json.dumps({"status": "failed", "error": str(exc)})


@tool(
    extras={
        "render_hint": "search_results",
        "category": "memory",
        "destructive": False,
        "icon": "search-check",
    }
)
async def search_memory(query: str, config: RunnableConfig, limit: int = 5) -> str:
    """Busca semântica em memórias — encontra memórias relevantes por similaridade.

    Diferente de ``get_memory`` (busca por chave exata), ``search_memory`` usa
    o índice vetorial do LangGraph BaseStore (Cohere embed quando configurado)
    para encontrar memórias semanticamente relacionadas à query.

    Args:
        query: Texto da busca semântica (ex: "preferências de código", "arquitetura")
        config: Injetado automaticamente pelo LangGraph
        limit: Máximo de memórias a retornar (padrão: 5)

    Returns:
        JSON com lista de memórias ordenadas por relevância semântica
    """
    try:
        store = _get_store()
        ns = _memory_namespace(config)

        items = await store.asearch(ns, query=query, limit=limit)
        has_scores = any(getattr(item, "score", None) is not None for item in items)

        memories = [
            {
                "key": item.key,
                "content": item.value.get("content", ""),
                "updated_at": item.value.get("updated_at"),
                **({"score": item.score} if has_scores else {}),
            }
            for item in items
        ]
        logger.debug(
            "search_memory query=%r count=%d semantic=%s",
            query,
            len(memories),
            has_scores,
        )
        return json.dumps(
            {
                "status": "success",
                "semantic": has_scores,
                "query": query,
                "count": len(memories),
                "memories": memories,
            }
        )

    except Exception as exc:
        logger.exception("search_memory_failed query=%r", query)
        return json.dumps({"status": "failed", "error": str(exc)})


@tool(
    extras={
        "render_hint": "json",
        "category": "memory",
        "destructive": True,
        "icon": "bookmark-x",
    }
)
async def delete_memory(key: str, config: RunnableConfig) -> str:
    """Deleta uma memória persistente do namespace do usuário.

    Args:
        key: Chave da memória a deletar
        config: Injetado automaticamente pelo LangGraph

    Returns:
        JSON com status deleted/not_found/failed
    """
    try:
        store = _get_store()
        ns = _memory_namespace(config)

        # Verifica se existe antes de deletar
        item = await store.aget(ns, key)
        if item is None:
            logger.warning("memory_not_found_for_deletion key=%s", key)
            return json.dumps({"status": "not_found", "key": key})

        await store.adelete(ns, key)
        logger.info("memory_deleted key=%s ns=%s", key, ns)
        return json.dumps({"status": "deleted", "key": key})

    except Exception as exc:
        logger.exception("delete_memory_failed key=%s", key)
        return json.dumps({"status": "failed", "error": str(exc), "key": key})

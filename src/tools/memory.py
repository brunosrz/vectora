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
    """Deriva namespace de memória a partir do contexto da sessão LangGraph.

    Prioridade (N1):
    1. user:<user_id>         — usuário autenticado; isolamento individual total.
    2. workspace_<id>         — workspace ativo; memórias seguem o projeto.
    3. session_<thread_id>    — fallback para isolamento por sessão simples.
    4. default_session        — chamado fora de um grafo LangGraph.

    O separador ':' em ``user:`` distingue visualmente de ``workspace_`` e
    ``session_`` (que usam '_') e evita colisões acidentais de namespace.
    """
    if config is None:
        return "default_session"
    configurable = config.get("configurable") or {}
    user_id = configurable.get("user_id")
    if user_id:
        return f"user:{user_id}"
    workspace_id = configurable.get("workspace_id")
    if workspace_id:
        return f"workspace_{workspace_id}"
    thread_id = configurable.get("thread_id")
    return f"session_{thread_id}" if thread_id else "default_session"


async def _embed_for_memory(text: str) -> list[float] | None:
    """Gera embedding Cohere para uma memória (C4). Retorna None se não configurado."""
    from src.config.settings import settings

    if not settings.memory_semantic_enabled:
        return None
    try:
        import cohere

        api_key = settings.get_cohere_api_key()
        if not api_key:
            return None
        client = cohere.AsyncClient(api_key=api_key)
        resp = await client.embed(
            texts=[text],
            model=settings.embedding_model,
            input_type="search_document",
        )
        embeddings = resp.embeddings
        if isinstance(embeddings, list) and embeddings:
            row = embeddings[0]
            return list(row) if not isinstance(row, list) else row
        return None
    except Exception:
        logger.debug("_embed_for_memory: falha ao embeddar", exc_info=True)
        return None


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

    As memórias são isoladas por workspace ou sessão para evitar poluição entre
    projetos distintos. São armazenadas no SQLite com embedding Cohere (C4) para
    busca semântica via `search_memory`.

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
        from src.services.memory import get_memory_store

        user_id = _user_id_from_config(config)
        memory_store = await get_memory_store()

        # C4 — Semantic Memory: gera embedding assincronamente
        embedding = await _embed_for_memory(content)

        memory_id = await memory_store.save(
            user_id=user_id,
            key=key,
            content=content,
            metadata=metadata,
            ttl_days=ttl_days,
            embedding=embedding,
        )

        logger.info(
            "memory_saved",
            extra={
                "key": key,
                "memory_id": memory_id,
                "ttl_days": ttl_days,
                "has_embedding": embedding is not None,
            },
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


@tool(
    extras={
        "render_hint": "json",
        "category": "memory",
        "destructive": False,
        "icon": "bookmark-check",
    }
)
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
        from src.services.memory import get_memory_store

        user_id = _user_id_from_config(config)
        memory_store = await get_memory_store()

        if key is not None:
            memory = await memory_store.get(user_id, key)
            # Dual-lookup: quando o namespace é workspace_*, tenta também o
            # namespace session_* legado para não perder memórias antigas (B7).
            if memory is None and user_id.startswith("workspace_"):
                thread_id = (config.get("configurable") or {}).get("thread_id")
                if thread_id:
                    memory = await memory_store.get(f"session_{thread_id}", key)
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
        # Dual-lookup: inclui memórias do namespace session_* legado (B7).
        if user_id.startswith("workspace_"):
            thread_id = (config.get("configurable") or {}).get("thread_id")
            if thread_id:
                legacy = await memory_store.get_all(f"session_{thread_id}")
                seen_keys = {m["key"] for m in all_memories}
                all_memories += [m for m in legacy if m["key"] not in seen_keys]
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


@tool(
    extras={
        "render_hint": "search_results",
        "category": "memory",
        "destructive": False,
        "icon": "search-check",
    }
)
async def search_memory(query: str, config: RunnableConfig, limit: int = 5) -> str:
    """Busca semântica em memórias — encontra memórias relevantes por similaridade (C4).

    Diferente de `get_memory` (busca por chave exata), `search_memory` usa embedding
    Cohere para encontrar memórias semanticamente relacionadas à query, mesmo que não
    contenham as palavras exatas. Ideal para "o que sei sobre X?" ou "decisões sobre Y?".

    Args:
        query: Texto da busca semântica (ex: "preferências de código", "arquitetura")
        config: Injetado automaticamente pelo LangGraph com workspace_id / thread_id
        limit: Máximo de memórias a retornar (padrão: 5)

    Returns:
        JSON com lista de memórias ordenadas por relevância semântica
    """
    try:
        from src.config.settings import settings
        from src.services.memory import get_memory_store

        user_id = _user_id_from_config(config)
        memory_store = await get_memory_store()

        if not settings.memory_semantic_enabled:
            # Fallback: retorna todas as memórias sem ranqueamento semântico
            all_mems = await memory_store.get_all(user_id)
            return json.dumps(
                {
                    "status": "success",
                    "semantic": False,
                    "count": len(all_mems[:limit]),
                    "memories": [
                        {
                            "key": m["key"],
                            "content": m["content"],
                            "score": None,
                            "updated_at": m["updated_at"],
                        }
                        for m in all_mems[:limit]
                    ],
                }
            )

        # C4 — embed query e busca por cosine similarity
        import cohere

        api_key = settings.get_cohere_api_key()
        if not api_key:
            logger.warning("search_memory: COHERE_API_KEY não configurada")
            all_mems = await memory_store.get_all(user_id)
            return json.dumps(
                {
                    "status": "success",
                    "semantic": False,
                    "count": len(all_mems[:limit]),
                    "memories": [
                        {
                            "key": m["key"],
                            "content": m["content"],
                            "score": None,
                            "updated_at": m["updated_at"],
                        }
                        for m in all_mems[:limit]
                    ],
                }
            )

        client = cohere.AsyncClient(api_key=api_key)
        resp = await client.embed(
            texts=[query],
            model=settings.embedding_model,
            input_type="search_query",
        )
        embeddings = resp.embeddings
        if not (isinstance(embeddings, list) and embeddings):
            raise ValueError("Cohere embed retornou lista vazia")
        row = embeddings[0]
        query_embedding = list(row) if not isinstance(row, list) else row

        results = await memory_store.search_semantic(user_id, query_embedding, limit)

        # Dual-lookup legado (B3/B7)
        if user_id.startswith("workspace_"):
            thread_id = (config.get("configurable") or {}).get("thread_id")
            if thread_id:
                legacy = await memory_store.search_semantic(
                    f"session_{thread_id}", query_embedding, limit
                )
                seen_keys = {m["key"] for m in results}
                results += [m for m in legacy if m["key"] not in seen_keys]
                results = results[:limit]

        logger.debug("search_memory: %d resultados semânticos", len(results))
        return json.dumps(
            {
                "status": "success",
                "semantic": True,
                "query": query,
                "count": len(results),
                "memories": [
                    {
                        "key": m["key"],
                        "content": m["content"],
                        "updated_at": m["updated_at"],
                    }
                    for m in results
                ],
            }
        )

    except Exception as e:
        logger.exception("search_memory_failed", extra={"query": query})
        return json.dumps({"status": "failed", "error": str(e)})


@tool(
    extras={
        "render_hint": "json",
        "category": "memory",
        "destructive": True,
        "icon": "bookmark-x",
    }
)
async def delete_memory(key: str, config: RunnableConfig) -> str:
    """Deleta uma memória persistente da sessão atual.

    Args:
        key: Chave da memória a deletar
        config: Injetado automaticamente pelo LangGraph com thread_id da sessão

    Returns:
        JSON com status deleted/not_found/failed
    """
    try:
        from src.services.memory import get_memory_store

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

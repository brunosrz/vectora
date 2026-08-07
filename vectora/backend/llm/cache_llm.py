"""Cache global de completions LLM.

``init_llm_cache()`` aplica um cache via ``langchain_core.globals.set_llm_cache``
conforme ``storage_mode`` e a disponibilidade do Redis:

- complete + Redis acessível + ``cache_semantic=False`` → ``RedisCache`` (exato)
- complete + Redis acessível + ``cache_semantic=True``  → ``RedisSemanticCache``
  (match por similaridade do prompt; usa os embeddings Cohere)
- caso contrário → ``InMemoryCache`` (por processo)

A escolha do Redis passa por ``redis_reachable()``; se o probe falhar, cai em
``InMemoryCache``. Idempotente — chamado no startup do servidor.
"""

from __future__ import annotations

import logging
from typing import Any, cast

logger = logging.getLogger(__name__)

# Cache atualmente aplicado (para introspecção em /admin/storage e testes).
_active_cache: Any = None


def init_llm_cache() -> Any:
    """Constrói e aplica o cache LLM global. Retorna a instância aplicada (ou None)."""
    global _active_cache

    from langchain_core.globals import set_llm_cache

    from backend.settings import settings

    if not settings.cache_llm_enabled:
        set_llm_cache(None)
        _active_cache = None
        logger.info("cache_llm: desativado (cache_llm_enabled=False)")
        return None

    cache = _build_cache()
    set_llm_cache(cache)
    _active_cache = cache
    logger.info("cache_llm: %s ativado", type(cache).__name__)
    return cache


def active_cache_name() -> str:
    """Nome da impl de cache LLM ativa (para o painel Admin → Storage)."""
    return type(_active_cache).__name__ if _active_cache is not None else "none"


def _redis_supports_cache(url: str) -> bool:
    """``True`` se o Redis tem os módulos RediSearch + RedisJSON.

    ``RedisCache``/``RedisSemanticCache`` usam ``JSON.GET``/``FT.*``; num Redis
    sem esses módulos (ex.: ``redis:alpine``) toda leitura de cache erra e
    derruba a chamada LLM. Exige ``redis-stack-server``.
    """
    try:
        import redis

        client = redis.from_url(url, socket_connect_timeout=0.5, decode_responses=True)
        try:
            modules = cast("list[dict[str, Any]]", client.module_list())
        finally:
            client.close()
        names = {str(m.get("name", "")).lower() for m in modules}
        return "search" in names and "rejson" in names
    except Exception:
        return False


def _build_cache() -> Any:
    from langchain_core.caches import InMemoryCache

    from backend.settings import settings

    url = (settings.redis_url or "").strip()
    if settings.storage_mode == "complete" and url:
        from backend.persistence.kv import redis_reachable

        if not redis_reachable(url):
            logger.info(
                "cache_llm: redis_url configurado mas inacessível — InMemoryCache"
            )
        elif not _redis_supports_cache(url):
            logger.info("cache_llm: Redis sem RediSearch/RedisJSON — InMemoryCache")
        else:
            try:
                return _build_redis_cache(url)
            except Exception as exc:
                logger.warning(
                    "cache_llm: falha ao criar cache Redis (%s) — InMemoryCache", exc
                )
    return InMemoryCache()


def _build_redis_cache(url: str) -> Any:
    from backend.settings import settings

    ttl = settings.cache_ttl_seconds or None

    if settings.cache_semantic:
        from backend.storage.factory import _build_lc_embeddings

        embeddings = _build_lc_embeddings()
        if embeddings is not None:
            from backend.llm.native_redis_cache import NativeRedisSemanticCache

            return NativeRedisSemanticCache(
                embeddings=embeddings,
                redis_url=url,
                distance_threshold=settings.cache_distance_threshold,
                ttl=ttl,
            )
        logger.warning(
            "cache_llm: cache_semantic=True mas sem embeddings Cohere — "
            "caindo para NativeRedisCache exato"
        )

    from backend.llm.native_redis_cache import NativeRedisCache

    return NativeRedisCache(redis_url=url, ttl=ttl)


def reset_llm_cache() -> None:
    """Desliga o cache LLM global. Para uso em testes."""
    global _active_cache
    try:
        from langchain_core.globals import set_llm_cache

        set_llm_cache(None)
    except Exception:
        pass
    _active_cache = None

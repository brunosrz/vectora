"""Cache LLM via Redis — cliente nativo (``redis``/``redis.asyncio``), sem
``langchain_redis``.

Continua implementando ``langchain_core.caches.BaseCache`` porque
``BaseChatModel._agenerate_with_cache`` (LangGraph/LangChain, camada agêntica
mantida por decisão desta sprint) só sabe falar com esse contrato — o ponto
de acoplamento ao framework aqui é o cache global do LangChain
(``set_llm_cache``), não a conexão Redis em si, que passa a ser 100% nativa.

Dois modos, escolhidos por ``settings.cache_semantic``:

- **Exato** (``NativeRedisCache``): chave = SHA-256 de ``(prompt, llm_string)``,
  ``SETEX`` de uma string.
- **Semântico** (``NativeRedisSemanticCache``): índice vetorial nativo via
  RediSearch (``FT.CREATE ... VECTOR HNSW`` sobre HASH), embedding do prompt
  via o mesmo provider já usado pelo RAG (``_build_lc_embeddings()``), busca
  KNN filtrada por ``llm_string`` e corte em ``distance_threshold``.
"""

from __future__ import annotations

import hashlib
import logging
import struct
from typing import TYPE_CHECKING, Any

from langchain_core.caches import RETURN_VAL_TYPE, BaseCache
from langchain_core.load import dumps, loads

if TYPE_CHECKING:
    from redis import Redis as SyncRedis
    from redis.asyncio import Redis as AsyncRedis

logger = logging.getLogger(__name__)

_EXACT_PREFIX = "vectora:cache:exact:"
_SEM_PREFIX = "vectora:cache:sem:"
_SEM_INDEX = "idx:vectora_llm_sem_cache"


def _exact_key(prompt: str, llm_string: str) -> str:
    digest = hashlib.sha256(f"{prompt}\x1f{llm_string}".encode()).hexdigest()
    return f"{_EXACT_PREFIX}{digest}"


def _llm_tag(llm_string: str) -> str:
    """Tag curta e sem caracteres especiais pra filtro TAG do RediSearch —
    o `llm_string` original fica guardado à parte pra checagem exata."""
    return hashlib.sha256(llm_string.encode()).hexdigest()[:16]


def _pack_vector(vector: list[float]) -> bytes:
    return struct.pack(f"<{len(vector)}f", *vector)


class NativeRedisCache(BaseCache):
    """Cache exato via Redis nativo — mesmo contrato do ``RedisCache`` do
    ``langchain_redis``, sem a dependência."""

    def __init__(self, redis_url: str, ttl: int | None = None) -> None:
        self._redis_url = redis_url
        self._ttl = ttl
        self._async_client: AsyncRedis | None = None
        self._sync_client: SyncRedis | None = None

    def _get_async_client(self) -> AsyncRedis:
        if self._async_client is None:
            import redis.asyncio as aredis

            self._async_client = aredis.from_url(self._redis_url)
        return self._async_client

    def _get_sync_client(self) -> SyncRedis:
        if self._sync_client is None:
            import redis

            self._sync_client = redis.from_url(self._redis_url)
        return self._sync_client

    # -- síncrono (exigido por BaseCache; caminho real do Vectora é async) --

    def lookup(self, prompt: str, llm_string: str) -> RETURN_VAL_TYPE | None:
        try:
            raw = self._get_sync_client().get(_exact_key(prompt, llm_string))
        except Exception:
            logger.debug("native_redis_cache: lookup síncrono falhou", exc_info=True)
            return None
        return loads(raw.decode(), allowed_objects="all") if raw else None  # ty: ignore[unresolved-attribute]

    def update(self, prompt: str, llm_string: str, return_val: RETURN_VAL_TYPE) -> None:
        try:
            client = self._get_sync_client()
            key = _exact_key(prompt, llm_string)
            value = dumps(return_val)
            if self._ttl:
                client.setex(key, self._ttl, value)
            else:
                client.set(key, value)
        except Exception:
            logger.debug("native_redis_cache: update síncrono falhou", exc_info=True)

    def clear(self, **kwargs: Any) -> None:
        try:
            client = self._get_sync_client()
            for key in client.scan_iter(match=f"{_EXACT_PREFIX}*"):
                client.delete(key)
        except Exception:
            logger.debug("native_redis_cache: clear síncrono falhou", exc_info=True)

    # -- assíncrono (caminho real: BaseChatModel._agenerate_with_cache) --

    async def alookup(self, prompt: str, llm_string: str) -> RETURN_VAL_TYPE | None:
        try:
            raw = await self._get_async_client().get(_exact_key(prompt, llm_string))
        except Exception:
            logger.debug("native_redis_cache: alookup falhou", exc_info=True)
            return None
        return loads(raw.decode(), allowed_objects="all") if raw else None

    async def aupdate(
        self, prompt: str, llm_string: str, return_val: RETURN_VAL_TYPE
    ) -> None:
        try:
            client = self._get_async_client()
            key = _exact_key(prompt, llm_string)
            value = dumps(return_val)
            if self._ttl:
                await client.setex(key, self._ttl, value)
            else:
                await client.set(key, value)
        except Exception:
            logger.debug("native_redis_cache: aupdate falhou", exc_info=True)

    async def aclear(self, **kwargs: Any) -> None:
        try:
            client = self._get_async_client()
            async for key in client.scan_iter(match=f"{_EXACT_PREFIX}*"):
                await client.delete(key)
        except Exception:
            logger.debug("native_redis_cache: aclear falhou", exc_info=True)


class NativeRedisSemanticCache(BaseCache):
    """Cache semântico via Redis nativo — índice vetorial RediSearch
    (HNSW/cosine) sobre HASH, sem ``langchain_redis``.

    Cada `llm_string` (modelo+params) tem seu próprio espaço lógico via TAG —
    um cache não vaza hit entre modelos/configs diferentes.
    """

    def __init__(
        self,
        embeddings: Any,
        redis_url: str,
        distance_threshold: float = 0.2,
        ttl: int | None = None,
    ) -> None:
        self._embeddings = embeddings
        self._redis_url = redis_url
        self._distance_threshold = distance_threshold
        self._ttl = ttl
        self._async_client: AsyncRedis | None = None
        self._sync_client: SyncRedis | None = None
        self._index_dim: int | None = None

    def _get_async_client(self) -> AsyncRedis:
        if self._async_client is None:
            import redis.asyncio as aredis

            self._async_client = aredis.from_url(self._redis_url)
        return self._async_client

    def _get_sync_client(self) -> SyncRedis:
        if self._sync_client is None:
            import redis

            self._sync_client = redis.from_url(self._redis_url)
        return self._sync_client

    async def _ensure_index(self, dim: int) -> None:
        if self._index_dim == dim:
            return
        client = self._get_async_client()
        try:
            info = await client.execute_command("FT.INFO", _SEM_INDEX)
            existing_dim = _extract_index_dim(info)
            if existing_dim == dim:
                self._index_dim = dim
                return
            # Dimensão mudou (provider de embedding trocou) — recria o índice.
            await client.execute_command("FT.DROPINDEX", _SEM_INDEX)
        except Exception:
            pass  # índice ainda não existe — cai no create abaixo

        await client.execute_command(
            "FT.CREATE",
            _SEM_INDEX,
            "ON",
            "HASH",
            "PREFIX",
            "1",
            _SEM_PREFIX,
            "SCHEMA",
            "llm_tag",
            "TAG",
            "vector",
            "VECTOR",
            "HNSW",
            "6",
            "TYPE",
            "FLOAT32",
            "DIM",
            str(dim),
            "DISTANCE_METRIC",
            "COSINE",
        )
        self._index_dim = dim

    async def alookup(self, prompt: str, llm_string: str) -> RETURN_VAL_TYPE | None:
        try:
            vector = await self._embeddings.aembed_query(prompt)
            await self._ensure_index(len(vector))

            client = self._get_async_client()
            tag = _llm_tag(llm_string)
            query = f"(@llm_tag:{{{tag}}})=>[KNN 1 @vector $vec AS score]"
            result = await client.execute_command(
                "FT.SEARCH",
                _SEM_INDEX,
                query,
                "PARAMS",
                "2",
                "vec",
                _pack_vector(vector),
                "SORTBY",
                "score",
                "ASC",
                "RETURN",
                "2",
                "return_val",
                "score",
                "DIALECT",
                "2",
            )
        except Exception:
            logger.debug("native_redis_cache: alookup semântico falhou", exc_info=True)
            return None

        hit = _parse_ft_search_top1(result)
        if hit is None:
            return None
        score, return_val_raw = hit
        # RediSearch devolve distância cosine (0 = idêntico); mesma semântica
        # de corte que RedisSemanticCache.
        if score > self._distance_threshold:
            return None
        return loads(return_val_raw, allowed_objects="all")

    async def aupdate(
        self, prompt: str, llm_string: str, return_val: RETURN_VAL_TYPE
    ) -> None:
        try:
            vector = await self._embeddings.aembed_query(prompt)
            await self._ensure_index(len(vector))

            client = self._get_async_client()
            digest = hashlib.sha256(f"{prompt}\x1f{llm_string}".encode()).hexdigest()
            key = f"{_SEM_PREFIX}{digest}"
            await client.hset(  # ty: ignore[invalid-await]
                key,
                mapping={
                    "llm_tag": _llm_tag(llm_string),
                    "return_val": dumps(return_val),
                    "vector": _pack_vector(vector),
                },
            )
            if self._ttl:
                await client.expire(key, self._ttl)
        except Exception:
            logger.debug("native_redis_cache: aupdate semântico falhou", exc_info=True)

    async def aclear(self, **kwargs: Any) -> None:
        try:
            client = self._get_async_client()
            async for key in client.scan_iter(match=f"{_SEM_PREFIX}*"):
                await client.delete(key)
        except Exception:
            logger.debug("native_redis_cache: aclear semântico falhou", exc_info=True)

    # -- síncrono (exigido por BaseCache; caminho real do Vectora é async) --

    def lookup(self, prompt: str, llm_string: str) -> RETURN_VAL_TYPE | None:
        try:
            vector = self._embeddings.embed_query(prompt)
            client = self._get_sync_client()
            tag = _llm_tag(llm_string)
            query = f"(@llm_tag:{{{tag}}})=>[KNN 1 @vector $vec AS score]"
            result = client.execute_command(
                "FT.SEARCH",
                _SEM_INDEX,
                query,
                "PARAMS",
                "2",
                "vec",
                _pack_vector(vector),
                "SORTBY",
                "score",
                "ASC",
                "RETURN",
                "2",
                "return_val",
                "score",
                "DIALECT",
                "2",
            )
        except Exception:
            logger.debug("native_redis_cache: lookup semântico falhou", exc_info=True)
            return None

        hit = _parse_ft_search_top1(result)
        if hit is None:
            return None
        score, return_val_raw = hit
        if score > self._distance_threshold:
            return None
        return loads(return_val_raw, allowed_objects="all")

    def update(self, prompt: str, llm_string: str, return_val: RETURN_VAL_TYPE) -> None:
        try:
            vector = self._embeddings.embed_query(prompt)
            client = self._get_sync_client()
            digest = hashlib.sha256(f"{prompt}\x1f{llm_string}".encode()).hexdigest()
            key = f"{_SEM_PREFIX}{digest}"
            client.hset(
                key,
                mapping={
                    "llm_tag": _llm_tag(llm_string),
                    "return_val": dumps(return_val),
                    "vector": _pack_vector(vector),
                },
            )
            if self._ttl:
                client.expire(key, self._ttl)
        except Exception:
            logger.debug("native_redis_cache: update semântico falhou", exc_info=True)

    def clear(self, **kwargs: Any) -> None:
        try:
            client = self._get_sync_client()
            for key in client.scan_iter(match=f"{_SEM_PREFIX}*"):
                client.delete(key)
        except Exception:
            logger.debug("native_redis_cache: clear semântico falhou", exc_info=True)


def _extract_index_dim(ft_info: Any) -> int | None:
    """Extrai o `DIM` do vetor a partir da resposta crua de `FT.INFO`."""
    try:
        flat = [
            item.decode() if isinstance(item, bytes) else item
            for item in _flatten(ft_info)
        ]
        for i, item in enumerate(flat):
            if item == "DIM" and i + 1 < len(flat):
                return int(flat[i + 1])
    except Exception:
        pass
    return None


def _flatten(obj: Any) -> list[Any]:
    out: list[Any] = []
    if isinstance(obj, (list, tuple)):
        for item in obj:
            out.extend(_flatten(item))
    elif isinstance(obj, dict):
        for k, v in obj.items():
            out.append(k)
            out.extend(_flatten(v))
    else:
        out.append(obj)
    return out


def _parse_ft_search_top1(result: Any) -> tuple[float, str] | None:
    """Extrai `(score, return_val)` do primeiro hit de `FT.SEARCH`.

    Formato bruto (RESP2): ``[total, doc_id, [field, value, field, value, ...]]``.
    Sem hit: ``total == 0``.
    """
    if not result or len(result) < 3:
        return None
    total = result[0]
    if isinstance(total, bytes):
        total = int(total)
    if not total:
        return None

    fields = result[2]
    pairs = {}
    for i in range(0, len(fields) - 1, 2):
        key = fields[i]
        key = key.decode() if isinstance(key, bytes) else key
        value = fields[i + 1]
        pairs[key] = value

    return_val_raw = pairs.get("return_val")
    score_raw = pairs.get("score")
    if return_val_raw is None or score_raw is None:
        return None

    if isinstance(return_val_raw, bytes):
        return_val_raw = return_val_raw.decode()
    score = float(score_raw)
    return score, return_val_raw

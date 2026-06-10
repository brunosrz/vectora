"""Factories singleton para backends de storage do Vectora.

Cada ``get_*()`` retorna sempre a mesma instância por processo (singleton
lazy). A impl concreta é escolhida por ``settings.storage_mode``:
    "lite"     — SQLite + LanceDB (default)
    "complete" — Postgres + Qdrant + Redis (Pro gate, F7+)

Wraps finos nesta fase: as factories delegam para os services existentes
sem alterar sua lógica. Quando F4-F8 forem implementados, os factories
passarão a instanciar os backends unificados.

Uso:
    from src.storage.factory import get_checkpointer, get_store

    async with await get_checkpointer() as cp:
        # cp é AsyncSqliteSaver ou AsyncPostgresSaver
        ...

    store = await get_store()   # AsyncSqliteStore ou PostgresStore
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Singletons por processo
# ---------------------------------------------------------------------------

_checkpointer_cm: Any = None  # context manager (AsyncSqliteSaver etc.)
_store: Any = None  # BaseStore
_pg_pool: Any = None  # asyncpg.Pool (complete mode only)
_vector_stores: dict[str, Any] = {}  # collection → lancedb.AsyncTable (raw)
_lc_vector_stores: dict[
    str, Any
] = {}  # "mode::path::collection" → LangChain VectorStore

# ---------------------------------------------------------------------------
# Checkpointer (F4 stub — wrap do Checkpointer existente)
# ---------------------------------------------------------------------------


def get_checkpointer(db_dsn: str | None = None) -> Any:
    """Retorna o context manager do checkpointer (F4: via AsyncConnectionPool).

    Usa o pool de conexões SQLite de F1 para criar o checkpointer com todos
    os PRAGMAs de hardening (WAL, busy_timeout, synchronous=NORMAL, etc.).

    Returns:
        Context manager (``async with``) que produz ``AsyncSqliteSaver``.

    Example::

        async with get_checkpointer() as cp:
            state = await cp.aget(config, ...)
    """
    from src.services.checkpoint import Checkpointer

    return Checkpointer(db_dsn=db_dsn)


# ---------------------------------------------------------------------------
# Store (F5 stub — wrap do build_store existente)
# ---------------------------------------------------------------------------


async def get_store(embedding_model: str | None = None) -> Any:
    """Retorna (ou cria) o BaseStore singleton.

    Wrap fino sobre ``src.services.backends.build_store()``.
    F5: usa ``AsyncSqliteStore`` (lite) persistente via aiosqlite dedicado.

    Returns:
        ``AsyncSqliteStore`` (lite) com índice Cohere opcional,
        já inicializado (``setup()`` chamado).
    """
    global _store
    if _store is None:
        from src.services.backends import build_store

        _store = await build_store(embedding_model)
        logger.debug("storage/factory: store criado (%s)", type(_store).__name__)
    return _store


# ---------------------------------------------------------------------------
# VectorStore raw (lancedb.AsyncTable — compatibilidade com código existente)
# ---------------------------------------------------------------------------


async def get_vector_store(
    collection: str = "articles",
    *,
    path: str | None = None,
) -> Any:
    """Retorna (ou cria) o ``lancedb.AsyncTable`` para ``collection``.

    Usado pelo background worker e pelos nós de RAG que operam na API baixo nível
    do LanceDB (escrita batch, índices IVF, FTS).  Para uso em chains LangChain,
    prefira ``get_langchain_vector_store()``.

    Args:
        collection: Nome da tabela/coleção LanceDB. Default ``"articles"``.
        path:       Diretório LanceDB. None = ``settings.lancedb_dir``.

    Returns:
        ``lancedb.AsyncTable`` ou None se a tabela não existir.
    """
    cache_key = f"{path or ''}::{collection}"
    if cache_key in _vector_stores:
        return _vector_stores[cache_key]

    from src.storage.lancedb.connection import get_lancedb

    db = await get_lancedb(path)
    try:
        table = await db.open_table(collection)
    except Exception:
        logger.debug("storage/factory: tabela %r não existe em %r", collection, path)
        table = None

    _vector_stores[cache_key] = table
    return table


# ---------------------------------------------------------------------------
# VectorStore LangChain (F6) — LanceDB lite · Qdrant HYBRID complete
# ---------------------------------------------------------------------------


async def get_langchain_vector_store(
    collection: str = "articles",
    *,
    mode: str | None = None,
    path: str | None = None,
) -> Any:
    """Retorna (ou cria) o LangChain ``VectorStore`` para ``collection``.

    Escolhe a implementação de acordo com ``mode`` (ou ``settings.storage_mode``):

    * **lite** — ``langchain_community.vectorstores.LanceDB`` apontando para
      o diretório LanceDB local. Integra com ``CohereEmbeddings`` e com os
      índices IVF/FTS criados pelo F1.

    * **complete** — ``langchain_qdrant.QdrantVectorStore`` com
      ``RetrievalMode.HYBRID`` (dense Cohere + sparse BM25). Requer
      ``settings.qdrant_url`` configurado.

    Collections padrão preservadas: ``articles``, ``web_cache``, ``search``.

    Args:
        collection: Nome da coleção / tabela. Default ``"articles"``.
        mode:       ``"lite"`` ou ``"complete"``. None = ``settings.storage_mode``.
        path:       Diretório LanceDB (lite only). None = ``settings.lancedb_dir``.

    Returns:
        ``langchain_core.vectorstores.VectorStore`` pronto para uso em chains.
    """
    from src.settings import settings as _s

    effective_mode = mode or _s.storage_mode
    cache_key = f"{effective_mode}::{path or ''}::{collection}"

    if cache_key in _lc_vector_stores:
        return _lc_vector_stores[cache_key]

    # Embeddings compartilhados (Cohere quando disponível, ou None para lite)
    embeddings = _build_lc_embeddings()

    if effective_mode == "lite":
        vs = _build_lancedb_vs(
            collection=collection,
            path=path or _s.lancedb_dir,
            embeddings=embeddings,
        )
    else:
        vs = _build_qdrant_vs(
            collection=collection,
            settings=_s,
            embeddings=embeddings,
        )

    _lc_vector_stores[cache_key] = vs
    logger.debug(
        "storage/factory: LangChain VectorStore criado mode=%s collection=%s",
        effective_mode,
        collection,
    )
    return vs


def _build_lc_embeddings() -> Any:
    """Retorna ``CohereEmbeddings`` se disponível, ou None (modo sem embeddings)."""
    try:
        from langchain_cohere import CohereEmbeddings

        from src.settings import settings as _s

        key = _s.get_cohere_api_key()
        model = _s.embedding_model
        if not key or not model:
            return None

        return CohereEmbeddings(  # ty: ignore[missing-argument]
            cohere_api_key=key,  # ty: ignore[invalid-argument-type]
            model=model,
        )
    except Exception:
        return None


def _build_lancedb_vs(
    collection: str,
    path: str | None,
    embeddings: Any,
) -> Any:
    """Constrói ``langchain_community.vectorstores.LanceDB``.

    Usa ``uri=`` (diretório LanceDB) e ``table_name=collection``. O mode de
    escrita é ``"append"`` para preservar documentos indexados anteriormente
    via background worker. Não requer que a tabela exista previamente — o
    LangChain VectorStore a criará na primeira operação de escrita.
    """
    import warnings

    from src.settings import settings as _s

    db_path = path or _s.lancedb_dir or ""
    if not db_path:
        import tempfile
        from pathlib import Path as _Path

        db_path = str(_Path(tempfile.gettempdir()) / "vectora_lancedb")
        logger.debug("storage/factory: lancedb_dir fallback para %s", db_path)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        from langchain_community.vectorstores import LanceDB

    vs = LanceDB(
        uri=db_path,
        embedding=embeddings,
        table_name=collection,
        mode="append",  # preserva docs existentes
    )
    return vs


def _build_qdrant_vs(
    collection: str,
    settings: Any,
    embeddings: Any,
) -> Any:
    """Constrói ``langchain_qdrant.QdrantVectorStore`` com modo HYBRID.

    Dense: ``CohereEmbeddings``. Sparse: BM25 automático via ``FastEmbedSparse``.
    Modo HYBRID: combina dense + sparse para recall máximo.

    Requer ``settings.qdrant_url`` configurado. Cria a coleção se não existir.
    """
    from langchain_qdrant import QdrantVectorStore, RetrievalMode
    from qdrant_client import QdrantClient

    client = QdrantClient(
        url=settings.qdrant_url or "http://localhost:6333",
        api_key=settings.qdrant_api_key,
    )

    sparse_embeddings = _build_sparse_embeddings()

    vs = QdrantVectorStore(
        client=client,
        collection_name=collection,
        embedding=embeddings,
        retrieval_mode=RetrievalMode.HYBRID
        if sparse_embeddings
        else RetrievalMode.DENSE,
        sparse_embedding=sparse_embeddings,
    )
    return vs


def _build_sparse_embeddings() -> Any:
    """Retorna ``FastEmbedSparse`` se disponível (para modo HYBRID no Qdrant)."""
    try:
        from langchain_qdrant import FastEmbedSparse

        return FastEmbedSparse(model_name="Qdrant/bm25")
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Asyncpg pool (F7 — complete mode)
# ---------------------------------------------------------------------------


async def get_pg_pool(dsn: str | None = None) -> Any:
    """Retorna (ou cria) o pool asyncpg compartilhado do modo complete.

    O pool é um singleton por processo — criado na primeira chamada e
    reutilizado em todas as chamadas subsequentes. Para fechar explicitamente
    (ex: teardown de testes) use ``close_pg_pool()``.

    Args:
        dsn: DSN asyncpg (``postgresql://user:pass@host/db``). None usa
             ``settings.postgres_dsn``. Deve ser asyncpg nativo (não
             ``postgresql+asyncpg://`` do SQLAlchemy).

    Returns:
        ``asyncpg.Pool`` configurado com min_size=2, max_size=20.

    Raises:
        RuntimeError: Se nenhum DSN estiver configurado.
    """
    global _pg_pool
    if _pg_pool is not None:
        return _pg_pool

    import asyncpg

    from src.settings import settings as _s

    effective_dsn = dsn or _s.postgres_dsn
    if not effective_dsn:
        msg = (
            "postgres_dsn não configurado. "
            "Defina POSTGRES_DSN no .env ou settings.json para usar o modo complete."
        )
        raise RuntimeError(msg)

    # asyncpg espera postgresql:// — normaliza se vier com +asyncpg do SQLAlchemy
    normalized = effective_dsn.replace("postgresql+asyncpg://", "postgresql://")

    _pg_pool = await asyncpg.create_pool(normalized, min_size=2, max_size=20)
    logger.debug("storage/factory: asyncpg pool criado dsn=%s", normalized[:30] + "…")
    return _pg_pool


async def close_pg_pool() -> None:
    """Fecha o pool asyncpg gracefully. Usado no shutdown do servidor e em testes."""
    global _pg_pool
    if _pg_pool is not None:
        await _pg_pool.close()
        _pg_pool = None
        logger.debug("storage/factory: asyncpg pool fechado")


# ---------------------------------------------------------------------------
# Health check agregado
# ---------------------------------------------------------------------------


async def storage_health() -> dict[str, Any]:
    """Retorna o status de saúde de todos os backends configurados.

    Usado pelo endpoint ``GET /admin/storage`` (F10) e pelo CLI
    ``vectora storage info`` (F11).

    Returns:
        ``{"checkpointer": {...}, "store": {...}, "lancedb": {...}, ...}``
    """
    result: dict[str, Any] = {}

    # Checkpointer — testa se o arquivo .db é acessível
    try:
        from src.settings import settings as _s

        db_path = _s.db_dsn
        if db_path:
            import aiosqlite

            async with aiosqlite.connect(db_path) as conn:
                await conn.execute("SELECT 1")
            result["checkpointer"] = {"ok": True, "error": None}
        else:
            result["checkpointer"] = {"ok": False, "error": "db_dsn não configurado"}
    except Exception as exc:
        result["checkpointer"] = {"ok": False, "error": str(exc)}

    # Store — verifica se o AsyncSqliteStore foi criado e a conexão está ativa
    try:
        store = await get_store()
        result["store"] = {"ok": store is not None, "error": None}
    except Exception as exc:
        result["store"] = {"ok": False, "error": str(exc)}

    # LanceDB — testa conexão e listagem de tabelas
    try:
        from src.storage.lancedb.connection import get_lancedb

        db = await get_lancedb()
        tables = await db.table_names()
        result["lancedb"] = {"ok": True, "error": None, "tables": list(tables)}
    except Exception as exc:
        result["lancedb"] = {"ok": False, "error": str(exc)}

    # Postgres — testado apenas no modo complete
    try:
        from src.settings import settings as _s

        if _s.storage_mode == "complete" and _s.postgres_dsn:
            pool = await get_pg_pool()
            async with pool.acquire() as conn:
                await conn.execute("SELECT 1")
            result["postgres"] = {"ok": True, "error": None}
        else:
            result["postgres"] = {"ok": None, "error": "não configurado (modo lite)"}
    except Exception as exc:
        result["postgres"] = {"ok": False, "error": str(exc)}

    # Redis — testado apenas no modo complete
    try:
        from src.settings import settings as _s

        if _s.storage_mode == "complete" and _s.redis_url:
            import redis.asyncio as aredis

            client = aredis.from_url(_s.redis_url)
            try:
                await client.ping()  # ty: ignore[invalid-await]
                result["redis"] = {"ok": True, "error": None}
            finally:
                await client.aclose()
        else:
            result["redis"] = {"ok": None, "error": "não configurado (modo lite)"}
    except Exception as exc:
        result["redis"] = {"ok": False, "error": str(exc)}

    # Config — resumo do modo de armazenamento e backends configurados
    # (sem expor segredos: apenas booleanos de "configurado").
    from src.settings import settings as _s

    result["config"] = {
        "storage_mode": _s.storage_mode,
        "postgres_configured": bool(_s.postgres_dsn),
        "redis_configured": bool(_s.redis_url),
        "qdrant_configured": bool(_s.qdrant_url),
    }

    return result


# ---------------------------------------------------------------------------
# Reset (usado em testes)
# ---------------------------------------------------------------------------


def _reset_singletons() -> None:
    """Limpa os singletons. Para uso exclusivo em testes."""
    global _store, _checkpointer_cm, _pg_pool
    _store = None
    _checkpointer_cm = None
    _pg_pool = None
    _vector_stores.clear()
    _lc_vector_stores.clear()

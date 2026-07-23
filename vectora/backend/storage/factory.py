"""Factories singleton para backends de storage do Vectora.

Cada ``get_*()`` retorna sempre a mesma instância por processo (singleton
lazy). A impl concreta é escolhida por ``settings.storage_mode``:
    "lite"     — SQLite + LanceDB (default)
    "complete" — Postgres + Qdrant + Redis (Pro gate, F7+)

Wraps finos nesta fase: as factories delegam para os services existentes
sem alterar sua lógica. Quando F4-F8 forem implementados, os factories
passarão a instanciar os backends unificados.

Uso:
    from backend.storage.factory import get_checkpointer, get_store

    async with await get_checkpointer() as cp:
        # cp é AsyncSqliteSaver ou AsyncPostgresSaver
        ...

    store = await get_store()   # AsyncSqliteStore ou PostgresStore

Garantia de produto — usuários/auth/settings/config NUNCA em Postgres:
``storage_mode`` ("lite"/"complete") afeta apenas checkpointer, BaseStore,
vector store e cache. Usuários, sessões, audit, invites
(``src/services/auth.py::_get_db``) e configurações (``runtime_settings``,
``~/.vectora/config.toml``) sempre vivem em SQLite/JSON/TOML, mesmo com
``storage_mode == "complete"`` — funcionam como fallback garantido
independente do banco principal.
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
    from backend.persistence.checkpoint import Checkpointer

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
        from backend.llm.backends import build_store

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

    from backend.storage.lancedb.connection import get_lancedb

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
    from backend.settings import settings as _s

    effective_mode = mode or _s.storage_mode
    cache_key = f"{effective_mode}::{path or ''}::{collection}"

    if cache_key in _lc_vector_stores:
        return _lc_vector_stores[cache_key]

    # Embeddings compartilhados (Cohere/Voyage/Ollama/OpenRouter conforme
    # credenciais + embedding_provider — None se nenhum configurado).
    embeddings = _build_lc_embeddings()
    if embeddings is not None:
        await _check_embedding_dimension(collection, embeddings)

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


def _build_cohere_embeddings() -> Any:
    """``CohereEmbeddings`` se a key Cohere estiver configurada, senão None."""
    try:
        from langchain_cohere import CohereEmbeddings

        from backend.settings import settings as _s

        key = _s.get_cohere_api_key()
        model = _s.embedding_model
        if not key or not model:
            return None

        return CohereEmbeddings(  # ty: ignore[missing-argument]
            cohere_api_key=key,
            model=model,
        )
    except Exception:
        return None


def _build_voyage_embeddings() -> Any:
    """``VoyageAIEmbeddings`` se a key VoyageAI estiver configurada, senão None."""
    try:
        from langchain_voyageai import VoyageAIEmbeddings

        from backend.settings import settings as _s

        key = _s.voyage_api_key
        model = _s.voyage_embedding_model
        if not key or not model:
            return None

        return VoyageAIEmbeddings(
            voyage_api_key=key,
            model=model,
        )
    except Exception:
        return None


def _build_ollama_embeddings(model_override: str | None = None) -> Any:
    """``OllamaEmbeddings`` se ``ollama_embedding_model`` (ou ``model_override``,
    vindo de ``rag_settings.embed_model`` em runtime) estiver configurado.

    Sem key (Ollama roda local) — o modelo é o próprio gate: None por default,
    nunca assume um modelo instalado no host do usuário."""
    try:
        from langchain_ollama import OllamaEmbeddings

        from backend.settings import settings as _s

        model = model_override or _s.ollama_embedding_model
        if not model:
            return None

        return OllamaEmbeddings(
            model=model,
            base_url=_s.ollama_base_url or "http://127.0.0.1:11434",
        )
    except Exception:
        return None


def _build_openrouter_embeddings(model_override: str | None = None) -> Any:
    """``OpenAIEmbeddings`` apontando pro base_url da OpenRouter (API
    compatível com OpenAI — mesmo cliente usado pro chat em
    ``services/utils.py::_build_concrete_model``). ``model_override`` vem de
    ``rag_settings.embed_model`` em runtime, quando setado."""
    try:
        from langchain_openai import OpenAIEmbeddings

        from backend.settings import settings as _s

        key = _s.openrouter_api_key
        model = model_override or _s.openrouter_embedding_model
        if not key or not model:
            return None

        return OpenAIEmbeddings(
            api_key=key,
            base_url="https://openrouter.ai/api/v1",
            model=model,
        )
    except Exception:
        return None


def _build_lc_embeddings() -> Any:
    """Embeddings com preferência configurável + fallback Cohere↔Voyage↔local.

    Ordem de resolução:
    1. ``rag_settings.embed_provider`` em runtime (aba de memória do
       workbench, ``PATCH /rag/settings``), se != "auto" e buildável — mesmo
       padrão que ``_build_reranker()`` já usa pra ``rerank_provider``. Sem
       isso a escolha do usuário na UI era só persistida, nunca lida aqui.
    2. ``settings.embedding_provider`` (env var ``EMBEDDING_PROVIDER``),
       se "auto"/vazio em runtime — respeita a escolha estática de quem não
       usa a UI (VPS/CLI).
    3. Cohere + Voyage juntos → ``FallbackEmbeddings`` (troca automática em
       quota esgotada, em runtime).
    4. Só um dos dois → esse.
    5. Nenhum dos dois → Ollama, depois OpenRouter (embeddings locais/gateway,
       sem custo de API hospedada — mas sem rerank: Cohere/Voyage-only).
    6. Nada configurado → None (modo sem embeddings).
    """
    from backend.settings import settings as _s
    from backend.workspace.runtime_settings import runtime_settings

    rag = runtime_settings.rag_settings
    runtime_pref = str(rag.get("embed_provider", "auto"))
    runtime_model = str(rag.get("embed_model") or "") or None

    builders: dict[str, Any] = {
        "cohere": _build_cohere_embeddings,
        "voyage": _build_voyage_embeddings,
        "ollama": lambda: _build_ollama_embeddings(runtime_model),
        "openrouter": lambda: _build_openrouter_embeddings(runtime_model),
    }
    preference = (
        runtime_pref if runtime_pref in builders else (_s.embedding_provider or "")
    )
    if preference in builders:
        preferred = builders[preference]()
        if preferred is not None:
            return preferred
        logger.warning(
            "storage/factory: embedding_provider=%r configurado mas sem "
            "credencial/modelo — caindo no fallback padrão",
            preference,
        )

    cohere = _build_cohere_embeddings()
    voyage = _build_voyage_embeddings()
    if cohere is not None and voyage is not None:
        from backend.llm.fallback_embeddings import FallbackEmbeddings

        return FallbackEmbeddings(
            cohere,
            voyage,
            primary_id=f"cohere:{_s.embedding_model}",
            secondary_id=f"voyage:{_s.voyage_embedding_model}",
        )
    if cohere or voyage:
        return cohere or voyage

    return _build_ollama_embeddings() or _build_openrouter_embeddings()


# ---------------------------------------------------------------------------
# Guard de dimensão — troca de embedding_provider sem reindex quebraria
# similarity search silenciosamente (vetores de dimensões diferentes na
# mesma coleção). Probe leve (uma chamada embed) na primeira construção do
# VectorStore por processo/coleção, comparado contra a dimensão persistida.
# ---------------------------------------------------------------------------


class EmbeddingDimensionMismatchError(Exception):
    """A coleção foi indexada com um embedding de dimensão diferente da
    configurada agora — reindexação necessária antes de buscar/inserir."""


async def _embedding_meta_db() -> Any:
    from backend.api.handlers.threads import _get_db as _threads_db

    return await _threads_db()


async def _ensure_embedding_meta_table(db: Any) -> None:
    await db.execute("""
        CREATE TABLE IF NOT EXISTS embedding_index_meta (
            collection TEXT PRIMARY KEY,
            provider   TEXT NOT NULL,
            dimension  INTEGER NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    await db.commit()


async def _check_embedding_dimension(collection: str, embeddings: Any) -> None:
    """Levanta ``EmbeddingDimensionMismatchError`` se a coleção já foi
    indexada com uma dimensão diferente da do embedding atual. Na primeira
    vez (sem registro), persiste a dimensão atual."""
    from datetime import UTC, datetime

    from backend.settings import settings as _s
    from backend.workspace.runtime_settings import runtime_settings

    probe = await embeddings.aembed_query("dimension probe")
    dimension = len(probe)
    runtime_pref = str(runtime_settings.rag_settings.get("embed_provider", "auto"))
    provider = (
        runtime_pref if runtime_pref != "auto" else (_s.embedding_provider or "auto")
    )

    db = await _embedding_meta_db()
    await _ensure_embedding_meta_table(db)
    async with db.execute(
        "SELECT provider, dimension FROM embedding_index_meta WHERE collection = ?",
        (collection,),
    ) as cur:
        row = await cur.fetchone()

    if row is None:
        await db.execute(
            "INSERT INTO embedding_index_meta (collection, provider, dimension, updated_at) "
            "VALUES (?, ?, ?, ?)",
            (collection, provider, dimension, datetime.now(UTC).isoformat()),
        )
        await db.commit()
        return

    existing_provider, existing_dimension = row
    if existing_dimension != dimension:
        msg = (
            f"Coleção {collection!r} foi indexada com embeddings de "
            f"{existing_dimension} dimensões (provider {existing_provider!r}), "
            f"mas o embedding configurado agora tem {dimension} dimensões "
            f"(provider {provider!r}). Reindexe a coleção (apague e reconstrua) "
            "antes de continuar, ou volte ao provider de embedding anterior."
        )
        raise EmbeddingDimensionMismatchError(msg)


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

    from backend.settings import settings as _s

    db_path = path or _s.lancedb_dir or ""
    if not db_path:
        import tempfile
        from pathlib import Path as _Path

        db_path = str(_Path(tempfile.gettempdir()) / "vectora_lancedb")
        logger.debug("storage/factory: lancedb_dir fallback para %s", db_path)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        from langchain_community.vectorstores import LanceDB

    return LanceDB(
        uri=db_path,
        embedding=embeddings,
        table_name=collection,
        mode="append",  # preserva docs existentes
    )


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

    from backend.rbac.subscription import require_pro

    require_pro()

    client = QdrantClient(
        url=settings.qdrant_url or "http://localhost:6333",
        api_key=settings.qdrant_api_key,
    )

    sparse_embeddings = _build_sparse_embeddings()

    return QdrantVectorStore(
        client=client,
        collection_name=collection,
        embedding=embeddings,
        retrieval_mode=RetrievalMode.HYBRID
        if sparse_embeddings
        else RetrievalMode.DENSE,
        sparse_embedding=sparse_embeddings,
    )


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


async def _ensure_postgres_schema(pool: Any) -> None:
    """Aplica migrations Postgres pendentes via PostgresMigrationRunner."""
    from backend.storage.migrations.postgres_runner import PostgresMigrationRunner

    try:
        async with pool.acquire() as conn:
            runner = PostgresMigrationRunner(conn)
            await runner.upgrade()
        logger.info("storage/factory: schema Postgres garantido via migrations")
    except Exception as exc:
        logger.warning("storage/factory: erro ao garantir schema Postgres: %s", exc)


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

    from backend.rbac.subscription import require_pro
    from backend.settings import settings as _s

    require_pro()

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
    await _ensure_postgres_schema(_pg_pool)
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
        from backend.settings import settings as _s

        db_path = _s.db_dsn
        if db_path:
            import aiosqlite

            async with aiosqlite.connect(db_path) as conn:
                await conn.execute("SELECT 1")
            result["checkpointer"] = {"ok": True, "error": None, "internal": True}
        else:
            result["checkpointer"] = {
                "ok": False,
                "error": "db_dsn não configurado",
                "internal": True,
            }
    except Exception as exc:
        result["checkpointer"] = {"ok": False, "error": str(exc), "internal": True}

    # Store — verifica se o AsyncSqliteStore foi criado e a conexão está ativa
    try:
        store = await get_store()
        result["store"] = {"ok": store is not None, "error": None, "internal": True}
    except Exception as exc:
        result["store"] = {"ok": False, "error": str(exc), "internal": True}

    # LanceDB — testa conexão e listagem de tabelas
    try:
        from backend.storage.lancedb.connection import get_lancedb

        db = await get_lancedb()
        tables = (await db.list_tables()).tables
        result["lancedb"] = {
            "ok": True,
            "error": None,
            "tables": list(tables),
            "internal": True,
        }
    except Exception as exc:
        result["lancedb"] = {"ok": False, "error": str(exc), "internal": True}

    # Postgres — testado apenas no modo complete
    try:
        from backend.settings import settings as _s

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
        from backend.settings import settings as _s

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
    from backend.settings import settings as _s
    from backend.workspace.runtime_settings import runtime_settings

    result["config"] = {
        "storage_mode": runtime_settings.storage_mode,
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

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

    store = get_store()   # InMemoryStore ou PostgresStore
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
_vector_stores: dict[str, Any] = {}  # name → VectorStore

# ---------------------------------------------------------------------------
# Checkpointer (F4 stub — wrap do Checkpointer existente)
# ---------------------------------------------------------------------------


async def get_checkpointer(db_dsn: str | None = None) -> Any:
    """Retorna o context manager do checkpointer.

    Wrap fino sobre ``src.services.checkpoint.Checkpointer``.
    F4 substituirá isso pelo pool F1 + AsyncSqliteSaver/AsyncPostgresSaver.

    Returns:
        Context manager que, ao entrar, produz um checkpointer LangGraph.
    """
    from src.services.checkpoint import Checkpointer

    return Checkpointer(db_dsn=db_dsn)


# ---------------------------------------------------------------------------
# Store (F5 stub — wrap do build_store existente)
# ---------------------------------------------------------------------------


def get_store(embedding_model: str | None = None) -> Any:
    """Retorna (ou cria) o BaseStore singleton.

    Wrap fino sobre ``src.services.backends.build_store()``.
    F5 substituirá pelo SqliteStore ou PostgresStore.

    Returns:
        ``InMemoryStore`` (lite) com índice Cohere opcional.
    """
    global _store
    if _store is None:
        from src.services.backends import build_store

        _store = build_store(embedding_model)
        logger.debug("storage/factory: store criado (%s)", type(_store).__name__)
    return _store


# ---------------------------------------------------------------------------
# VectorStore (F6 stub — wrap do LanceDB existente)
# ---------------------------------------------------------------------------


async def get_vector_store(
    collection: str = "articles",
    *,
    path: str | None = None,
) -> Any:
    """Retorna (ou cria) o VectorStore para ``collection``.

    Wrap fino sobre a conexão LanceDB via ``src.storage.lancedb.get_lancedb()``.
    F6 substituirá pelo ``LangChain VectorStore`` completo.

    Args:
        collection: Nome da tabela/coleção LanceDB. Default ``"articles"``.
        path:       Diretório LanceDB. None = ``settings.lancedb_dir``.

    Returns:
        ``lancedb.AsyncTable``
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

    # Store — só verifica se foi criado (InMemoryStore não tem I/O)
    try:
        store = get_store()
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

    return result


# ---------------------------------------------------------------------------
# Reset (usado em testes)
# ---------------------------------------------------------------------------


def _reset_singletons() -> None:
    """Limpa os singletons. Para uso exclusivo em testes."""
    global _store, _checkpointer_cm
    _store = None
    _checkpointer_cm = None
    _vector_stores.clear()

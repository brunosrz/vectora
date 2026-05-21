"""LangGraph Checkpoint Management for Conversation State Persistence.

Manages SQLite-backed checkpointing for LangGraph execution state.
Enables resuming interrupted conversations, thread-level history,
and state snapshots for debugging and auditing."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from vectora.config.settings import settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def Checkpointer(
    db_dsn: str | None = None,
) -> AsyncGenerator[AsyncSqliteSaver]:
    """Constrói checkpointer SQLite assíncrono para persistência local de conversas.

    Usa aiosqlite via AsyncSqliteSaver do LangGraph. O arquivo SQLite é criado
    automaticamente no diretório `data/` na raiz do projeto.

    **Concorrência:** WAL mode habilitado automaticamente para permitir
    leituras simultâneas enquanto o BackgroundWorker escreve embeddings.

    Args:
        db_dsn: Caminho para o arquivo SQLite. Se None, usa o padrão de `settings.db_dsn`.
    """
    conn_string = db_dsn or settings.db_dsn
    if conn_string is None:
        msg = "db_dsn not configured"
        raise RuntimeError(msg)
    async with AsyncSqliteSaver.from_conn_string(conn_string) as checkpointer:
        # Enable WAL mode for concurrent reads + writes
        # Critical: Chat reads/writes messages while BackgroundWorker accesses queue
        try:
            await checkpointer.conn.execute("PRAGMA journal_mode=WAL;")
            await checkpointer.conn.execute("PRAGMA synchronous=NORMAL;")
            logger.info("Checkpointer: WAL mode enabled for concurrent access")
        except Exception as e:
            logger.warning("Could not enable WAL mode", extra={"error": str(e)})

        yield checkpointer

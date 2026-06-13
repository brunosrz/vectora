"""SessionService: Manages chat session lifecycle and context.

Responsibilities:
1. Create, switch, list, delete chat sessions
2. Generate runnable configs for LangGraph execution
3. Maintain session metadata (user_type, created_at, etc.)
4. Persist session state to database

Implementation: Ports AsyncSqliteSaver logic from checkpointer.py
"""

import json
import logging
import random
from datetime import UTC, datetime

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.types import RunnableConfig

from src.settings import Settings

logger = logging.getLogger(__name__)


_SESSION_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS vectora_sessions (
    thread_id     TEXT    PRIMARY KEY,
    user_type     TEXT    NOT NULL DEFAULT 'default',
    created_at    TEXT    NOT NULL,
    last_activity TEXT    NOT NULL,
    message_count INTEGER NOT NULL DEFAULT 0,
    extra         TEXT    NOT NULL DEFAULT '{}'
);
"""


def _generate_session_id() -> str:
    """Gera ID de sessão de 6 dígitos com zero-padding.

    Exemplos: '042731', '000101', '999999'.
    Armazenado como string para preservar zeros à esquerda.
    """
<<<<<<< HEAD:vectora/services/session.py
    return f"{random.randint(0, 999_999):06d}"  # noqa: S311 — não é criptográfico, apenas ID de sessão
=======
    return f"{random.randint(0, 999_999):06d}"  # noqa: S311  # nosec B311 — não é criptográfico, apenas ID de sessão legível
>>>>>>> dev:src/services/session.py


class SessionService:
    """Manages chat session lifecycle with database persistence.

    Features:
    - SQLite-backed session persistence (AsyncSqliteSaver + vectora_sessions table)
    - WAL mode for concurrent reads/writes
    - Session metadata tracking (created_at, last_activity)
    - Session creation and switching
    - History management per session

    Decisão D1 (reset limpo): na startup, os metadados são carregados do banco.
    Se o banco estiver corrompido ou ausente, a tabela é recriada vazia sem migração.
    """

    def __init__(self, settings: Settings):
        """Initialize SessionService.

        Args:
            settings: Application settings
        """
        self.settings = settings
        self.checkpointer: AsyncSqliteSaver | None = None
        self._checkpointer_context = None  # Keep context manager alive
        self._session_cache: dict[str, dict] = {}  # In-memory mirror do banco (str key)

        logger.debug("SessionService initialized")

    async def initialize(self) -> None:
        """Initialize database connection and load persisted sessions.

        Called from AgentManager.initialize().
        Sets up AsyncSqliteSaver with WAL mode and loads session metadata
        from the vectora_sessions table (D1: reset limpo — cria a tabela
        do zero se não existir, sem migração de dados corrompidos).
        """
        try:
            # Create context manager and enter it (keep it alive during app lifetime)
            db_dsn = self.settings.db_dsn
            if db_dsn is None:
                msg = "db_dsn not configured"
                raise RuntimeError(msg)
            self._checkpointer_context = AsyncSqliteSaver.from_conn_string(db_dsn)
            self.checkpointer = await self._checkpointer_context.__aenter__()

            # Enable WAL mode for concurrent access
            await self.checkpointer.conn.execute("PRAGMA journal_mode=WAL;")
            await self.checkpointer.conn.execute("PRAGMA synchronous=NORMAL;")

            # Create session metadata table (idempotent)
            await self.checkpointer.conn.execute(_SESSION_TABLE_DDL)
            await self.checkpointer.conn.commit()

            # Load existing sessions into memory cache
            await self._load_sessions_from_db()

            logger.info(
                "SessionService: Database initialized with WAL mode (%d sessions loaded)",
                len(self._session_cache),
            )
        except Exception as e:
            logger.exception(f"Failed to initialize database: {e}")
            raise

    async def _load_sessions_from_db(self) -> None:
        """Carrega metadados de sessões do banco para o cache em memória."""
        if not self.checkpointer:
            return
        try:
            cursor = await self.checkpointer.conn.execute(
                "SELECT thread_id, user_type, created_at, last_activity, message_count, extra "
                "FROM vectora_sessions ORDER BY last_activity DESC"
            )
            rows = await cursor.fetchall()
            self._session_cache = {}
            for row in rows:
                (
                    thread_id,
                    user_type,
                    created_at,
                    last_activity,
                    message_count,
                    extra,
                ) = row
                extra_data = json.loads(extra) if extra else {}
                self._session_cache[thread_id] = {
                    "thread_id": thread_id,
                    "user_type": user_type,
                    "created_at": created_at,
                    "last_activity": last_activity,
                    "message_count": message_count,
                    **extra_data,
                }
        except Exception as e:
            logger.warning("SessionService: erro ao carregar sessions do banco (%s)", e)
            self._session_cache = {}

    async def _persist_session(self, metadata: dict) -> None:
        """Insere ou atualiza metadados de uma sessão no banco."""
        if not self.checkpointer:
            return
        try:
            thread_id = metadata["thread_id"]
            extra = {
                k: v
                for k, v in metadata.items()
                if k
                not in {
                    "thread_id",
                    "user_type",
                    "created_at",
                    "last_activity",
                    "message_count",
                }
            }
            await self.checkpointer.conn.execute(
                """INSERT INTO vectora_sessions
                   (thread_id, user_type, created_at, last_activity, message_count, extra)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(thread_id) DO UPDATE SET
                     last_activity = excluded.last_activity,
                     message_count = excluded.message_count,
                     extra = excluded.extra
                """,
                (
                    thread_id,
                    metadata.get("user_type", "default"),
                    metadata.get("created_at", datetime.now(UTC).isoformat()),
                    metadata.get("last_activity", datetime.now(UTC).isoformat()),
                    metadata.get("message_count", 0),
                    json.dumps(extra),
                ),
            )
            await self.checkpointer.conn.commit()
        except Exception as e:
            logger.warning("SessionService: erro ao persistir session (%s)", e)

    async def create(
        self,
        user_type: str = "default",
        working_directory: str | None = None,
    ) -> str:
        """Create new chat session.

        Args:
            user_type: User classification ("default" or custom)
            working_directory: The working directory (cwd) where the session was created.
                Stored in session.extra so /sessions can show it.

        Returns:
            New session/thread ID (6-digit zero-padded string, e.g. '042731')
        """
        # Gera ID aleatório de 6 dígitos, garantindo unicidade no cache
        new_thread_id = _generate_session_id()
        while new_thread_id in self._session_cache:
            new_thread_id = _generate_session_id()

        # Create session metadata
        created_at = datetime.now(UTC).isoformat()
        session_metadata: dict = {
            "thread_id": new_thread_id,
            "user_type": user_type,
            "created_at": created_at,
            "last_activity": created_at,
            "message_count": 0,
        }
        if working_directory:
            session_metadata["working_directory"] = working_directory

        # Store in cache and persist to database
        self._session_cache[new_thread_id] = session_metadata
        await self._persist_session(session_metadata)

        logger.info(
            "Session created",
            extra={
                "thread_id": new_thread_id,
                "user_type": user_type,
                "working_directory": working_directory,
            },
        )

        return new_thread_id

    async def switch(self, thread_id: str) -> bool:
        """Switch to existing session.

        Args:
            thread_id: Session ID to activate

        Returns:
            True if session exists, False otherwise
        """
        # Check if session exists in cache
        if thread_id not in self._session_cache:
            logger.warning(f"Session not found: {thread_id}")
            return False

        # Update last activity
        self._session_cache[thread_id]["last_activity"] = datetime.now(UTC).isoformat()

        logger.info(f"Switched to session: {thread_id}")
        return True

    async def list_all(self) -> list[dict]:
        """Get all available sessions.

        Returns:
            List of session metadata dicts, sorted by last_activity (newest first)
        """
        sessions = list(self._session_cache.values())

        # Sort by last_activity descending
        sessions.sort(
            key=lambda s: s.get("last_activity", ""),
            reverse=True,
        )

        logger.debug(f"Listed {len(sessions)} sessions")
        return sessions

    def get_runnable_config(self, thread_id: str) -> RunnableConfig:
        """Get LangGraph runnable config for session.

        Phase 2 Refactor: No longer injects Context in configurable.
        Instead, session_metadata is part of State (JSON-serializable).

        Args:
            thread_id: Session ID

        Returns:
            RunnableConfig with just thread_id (metadata goes in State)
        """
        return RunnableConfig(
            configurable={
                "thread_id": thread_id,
            }
        )

    async def delete(self, thread_id: str) -> bool:
        """Delete session and its history.

        Args:
            thread_id: Session to delete

        Returns:
            True if deleted, False if not found
        """
        if thread_id not in self._session_cache:
            logger.warning(f"Session not found for deletion: {thread_id}")
            return False

        del self._session_cache[thread_id]

        # Remove from database
        if self.checkpointer:
            try:
                await self.checkpointer.conn.execute(
                    "DELETE FROM vectora_sessions WHERE thread_id = ?", (thread_id,)
                )
                await self.checkpointer.conn.commit()
            except Exception as e:
                logger.warning(
                    "SessionService: erro ao deletar session do banco (%s)", e
                )

        logger.warning(f"Session deleted: {thread_id}")
        return True

    async def get_history(self, thread_id: str, limit: int = 50) -> list[dict]:
        """Get message history for session.

        Args:
            thread_id: Session ID
            limit: Maximum messages to return

        Returns:
            List of messages with role and content
        """
        if not self.checkpointer:
            logger.warning("Database not initialized")
            return []

        try:
            # Query checkpoint history for this thread
            # Note: Full implementation would query message store
            # For now, return placeholder that could be expanded
            logger.debug(f"Retrieved history for session {thread_id}")
            return []

        except Exception as e:
            logger.exception(f"Failed to get history: {e}")
            return []

    async def update_activity(self, thread_id: str) -> None:
        """Update last activity timestamp for session and persist.

        Args:
            thread_id: Session ID
        """
        if thread_id in self._session_cache:
            self._session_cache[thread_id]["last_activity"] = datetime.now(
                UTC
            ).isoformat()

            # Also update message count if tracking
            session = self._session_cache[thread_id]
            session["message_count"] = session.get("message_count", 0) + 1
            await self._persist_session(session)

    async def shutdown(self) -> None:
        """Gracefully close database connection.

        Called from AgentManager.shutdown().
        """
        if self._checkpointer_context:
            try:
                await self._checkpointer_context.__aexit__(None, None, None)
                logger.info("SessionService: Database connection closed")
            except Exception as e:
                logger.exception(f"Error closing database: {e}")

        self.checkpointer = None
        self._checkpointer_context = None


# ---------------------------------------------------------------------------
# Backend Postgres — SessionDB protocol (F7 — complete mode)
# ---------------------------------------------------------------------------


class PostgresSessionDB:
    """Implementação Postgres do protocolo ``SessionDB``.

    Gere as tabelas ``vectora_sessions`` e ``vectora_checkpoint_artifacts``
    via pool asyncpg de ``storage.factory.get_pg_pool()``.
    """

    async def health(self) -> dict[str, object]:
        """Verifica se a conexão Postgres está acessível."""
        try:
            from src.storage.factory import get_pg_pool

            pool = await get_pg_pool()
            async with pool.acquire() as conn:
                await conn.execute("SELECT 1")
            return {"ok": True, "error": None}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    async def create_session(
        self,
        thread_id: str,
        user_type: str = "human",
        extra: str = "{}",
    ) -> None:
        """Cria ou ignora uma sessão existente."""
        from datetime import UTC, datetime

        from src.storage.factory import get_pg_pool

        now = datetime.now(UTC).isoformat()
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO vectora_sessions
                    (thread_id, user_type, created_at, last_activity,
                     message_count, extra)
                VALUES ($1, $2, $3, $3, 0, $4)
                ON CONFLICT (thread_id) DO NOTHING
                """,
                thread_id,
                user_type,
                now,
                extra,
            )

    async def get_session(self, thread_id: str) -> dict[str, object] | None:
        """Retorna os metadados da sessão ou None."""
        from src.storage.factory import get_pg_pool

        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM vectora_sessions WHERE thread_id = $1", thread_id
            )
        return dict(row) if row else None

    async def list_sessions(self, *, limit: int = 50) -> list[dict[str, object]]:
        """Lista sessões ordenadas por atividade recente."""
        from src.storage.factory import get_pg_pool

        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM vectora_sessions
                ORDER BY last_activity DESC
                LIMIT $1
                """,
                limit,
            )
        return [dict(r) for r in rows]

    async def delete_session(self, thread_id: str) -> None:
        """Remove a sessão e seus artifacts."""
        from src.storage.factory import get_pg_pool

        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM vectora_sessions WHERE thread_id = $1", thread_id
            )

    async def update_activity(self, thread_id: str) -> None:
        """Atualiza ``last_activity`` e incrementa ``message_count``."""
        from datetime import UTC, datetime

        from src.storage.factory import get_pg_pool

        now = datetime.now(UTC).isoformat()
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE vectora_sessions
                SET last_activity = $2,
                    message_count = message_count + 1
                WHERE thread_id = $1
                """,
                thread_id,
                now,
            )

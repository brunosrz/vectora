"""ListThreads filtra threads vazias (message_count=0) e cleanup_empty_threads
apaga as antigas o suficiente — UX-1 do plano de pré-lançamento (sessões
fantasma na sidebar, resíduo de threads nunca usadas).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from backend.api.handlers.threads import (
    ListThreadsRequest,
    _ensure_schema,
    cleanup_empty_threads,
    list_threads,
)


@pytest.fixture
async def mem_db():
    import aiosqlite

    db = await aiosqlite.connect(":memory:")
    await _ensure_schema(db)
    return db


@pytest.fixture(autouse=True)
def patch_get_db(mem_db):
    with patch(
        "backend.api.handlers.threads._get_db", new=AsyncMock(return_value=mem_db)
    ):
        yield mem_db


async def _insert_session(
    db, thread_id: str, message_count: int, created_at: str
) -> None:
    await db.execute(
        "INSERT INTO vectora_sessions "
        "(thread_id, created_at, last_activity, message_count, extra) "
        "VALUES (?, ?, ?, ?, ?)",
        (thread_id, created_at, created_at, message_count, "{}"),
    )
    await db.commit()


class TestListThreadsFiltersEmpty:
    @pytest.mark.asyncio
    async def test_omits_threads_with_zero_messages(self, mem_db):
        now = datetime.now(UTC).isoformat()
        await _insert_session(mem_db, "empty1", 0, now)
        await _insert_session(mem_db, "real1", 2, now)

        out = await list_threads(ListThreadsRequest(limit=50))

        ids = [t.id for t in out.threads]
        assert ids == ["real1"]

    @pytest.mark.asyncio
    async def test_empty_db_returns_empty_list(self, mem_db):
        out = await list_threads(ListThreadsRequest(limit=50))
        assert out.threads == []


class TestCleanupEmptyThreads:
    @pytest.mark.asyncio
    async def test_deletes_only_old_empty_threads(self, mem_db):
        old = (datetime.now(UTC) - timedelta(hours=2)).isoformat()
        recent = (datetime.now(UTC) - timedelta(minutes=5)).isoformat()
        await _insert_session(mem_db, "ghost-old", 0, old)
        await _insert_session(mem_db, "ghost-recent", 0, recent)
        await _insert_session(mem_db, "real-old", 3, old)

        deleted = await cleanup_empty_threads(max_age_hours=1.0)

        async with mem_db.execute(
            "SELECT thread_id FROM vectora_sessions ORDER BY thread_id"
        ) as cur:
            remaining = {row[0] for row in await cur.fetchall()}

        assert deleted == 1
        assert remaining == {"ghost-recent", "real-old"}

    @pytest.mark.asyncio
    async def test_no_empty_threads_deletes_nothing(self, mem_db):
        now = datetime.now(UTC).isoformat()
        await _insert_session(mem_db, "real1", 1, now)

        deleted = await cleanup_empty_threads(max_age_hours=1.0)

        assert deleted == 0


class TestCleanupOrphanedThreadsWithoutCheckpoint:
    """message_count > 0 sem nenhum checkpoint real do LangGraph — sinal de
    que o grafo nunca rodou pra essa thread (bug histórico do stream_chat:
    message_count incrementado antes do agente inicializar). Sem essa
    passada extra, essas threads ficam fantasma pra sempre — passam no
    filtro `message_count > 0` do ListThreads e a 1ª passada do cleanup só
    olha `message_count = 0`."""

    @staticmethod
    async def _create_checkpoints_table(db) -> None:
        await db.execute(
            "CREATE TABLE checkpoints (thread_id TEXT, checkpoint_id TEXT)"
        )
        await db.commit()

    @staticmethod
    async def _insert_checkpoint(db, thread_id: str) -> None:
        await db.execute(
            "INSERT INTO checkpoints (thread_id, checkpoint_id) VALUES (?, ?)",
            (thread_id, "cp1"),
        )
        await db.commit()

    @pytest.mark.asyncio
    async def test_deletes_old_thread_with_message_count_but_no_checkpoint(
        self, mem_db
    ):
        await self._create_checkpoints_table(mem_db)
        old = (datetime.now(UTC) - timedelta(hours=2)).isoformat()
        await _insert_session(mem_db, "phantom-old", 1, old)

        deleted = await cleanup_empty_threads(max_age_hours=1.0)

        async with mem_db.execute("SELECT thread_id FROM vectora_sessions") as cur:
            remaining = {row[0] for row in await cur.fetchall()}
        assert deleted == 1
        assert remaining == set()

    @pytest.mark.asyncio
    async def test_keeps_old_thread_with_real_checkpoint(self, mem_db):
        await self._create_checkpoints_table(mem_db)
        old = (datetime.now(UTC) - timedelta(hours=2)).isoformat()
        await _insert_session(mem_db, "real-old-cp", 1, old)
        await self._insert_checkpoint(mem_db, "real-old-cp")

        deleted = await cleanup_empty_threads(max_age_hours=1.0)

        async with mem_db.execute("SELECT thread_id FROM vectora_sessions") as cur:
            remaining = {row[0] for row in await cur.fetchall()}
        assert deleted == 0
        assert remaining == {"real-old-cp"}

    @pytest.mark.asyncio
    async def test_keeps_recent_thread_without_checkpoint(self, mem_db):
        """Não apaga sessão recente sem checkpoint — pode estar no meio do
        1º turno (grafo ainda rodando, checkpoint ainda não commitado)."""
        await self._create_checkpoints_table(mem_db)
        recent = (datetime.now(UTC) - timedelta(minutes=1)).isoformat()
        await _insert_session(mem_db, "in-flight", 1, recent)

        deleted = await cleanup_empty_threads(max_age_hours=1.0)

        async with mem_db.execute("SELECT thread_id FROM vectora_sessions") as cur:
            remaining = {row[0] for row in await cur.fetchall()}
        assert deleted == 0
        assert remaining == {"in-flight"}

    @pytest.mark.asyncio
    async def test_no_checkpoints_table_does_not_crash(self, mem_db):
        """Sem a tabela `checkpoints` (ex.: banco novo, agente nunca rodou),
        a 2ª passada é pulada de forma segura — não derruba a 1ª passada."""
        old = (datetime.now(UTC) - timedelta(hours=2)).isoformat()
        await _insert_session(mem_db, "empty-old", 0, old)
        await _insert_session(mem_db, "has-count-old", 1, old)

        deleted = await cleanup_empty_threads(max_age_hours=1.0)

        async with mem_db.execute("SELECT thread_id FROM vectora_sessions") as cur:
            remaining = {row[0] for row in await cur.fetchall()}
        assert deleted == 1
        assert remaining == {"has-count-old"}

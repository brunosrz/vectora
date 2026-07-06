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

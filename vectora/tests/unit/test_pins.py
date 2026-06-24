"""Pins de sessão — persistência no backend (WB-1).

Contrato:
1. _set_session_pins() grava a lista em vectora_sessions.extra["pins"],
   mesclando (preserva title/mode/workspace_id já gravados).
2. _get_session_pins() lê a lista de volta; thread inexistente → [].
3. Normalização: dedup, trim, backslash→slash, descarta vazios.
4. Endpoints GetThreadPins/SetThreadPins fazem o round-trip via RPC.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import aiosqlite
import pytest

from backend.api.handlers import threads


@pytest.fixture
async def fake_db():
    db = await aiosqlite.connect(":memory:")
    await db.execute(
        """
        CREATE TABLE vectora_sessions (
            thread_id     TEXT PRIMARY KEY,
            user_type     TEXT,
            created_at    TEXT,
            last_activity TEXT,
            message_count INTEGER NOT NULL DEFAULT 0,
            extra         TEXT    NOT NULL DEFAULT '{}'
        )
        """
    )
    await db.commit()
    try:
        yield db
    finally:
        await db.close()


async def _extra(db: aiosqlite.Connection, thread_id: str) -> dict:
    async with db.execute(
        "SELECT extra FROM vectora_sessions WHERE thread_id = ?", (thread_id,)
    ) as cur:
        row = await cur.fetchone()
    return json.loads(row[0]) if row else {}


# ---------------------------------------------------------------------------
# Helpers de persistência
# ---------------------------------------------------------------------------


class TestSessionPinsPersistence:
    async def test_set_then_get_roundtrip(self, fake_db):
        with patch.object(threads, "_get_db", AsyncMock(return_value=fake_db)):
            await threads._set_session_pins("t1", ["src/a.py", "README.md"])
            pins = await threads._get_session_pins("t1")
        assert pins == ["src/a.py", "README.md"]

    async def test_get_missing_thread_is_empty(self, fake_db):
        """Borda: thread sem registro → lista vazia, nunca erro."""
        with patch.object(threads, "_get_db", AsyncMock(return_value=fake_db)):
            assert await threads._get_session_pins("nao-existe") == []

    async def test_set_preserves_other_extra_keys(self, fake_db):
        """Pins não podem apagar title/mode/workspace_id já gravados."""
        with patch.object(threads, "_get_db", AsyncMock(return_value=fake_db)):
            await threads._upsert_session(
                "t2", title="Olá", workspace_id="ws1", mode="dev"
            )
            await threads._set_session_pins("t2", ["a.py"])
            extra = await _extra(fake_db, "t2")
        assert extra["title"] == "Olá"
        assert extra["workspace_id"] == "ws1"
        assert extra["mode"] == "dev"
        assert extra["pins"] == ["a.py"]

    async def test_normalizes_dedup_trim_slash_and_drops_empty(self, fake_db):
        """Erro/borda: entrada suja (duplicados, espaços, backslash, vazios)."""
        with patch.object(threads, "_get_db", AsyncMock(return_value=fake_db)):
            cleaned = await threads._set_session_pins(
                "t3",
                ["src\\a.py", "  src/a.py  ", "", "   ", "b.py", "b.py"],
            )
        assert cleaned == ["src/a.py", "b.py"]

    async def test_set_empty_clears(self, fake_db):
        """Borda: setar lista vazia zera os pins."""
        with patch.object(threads, "_get_db", AsyncMock(return_value=fake_db)):
            await threads._set_session_pins("t4", ["a.py"])
            await threads._set_session_pins("t4", [])
            assert await threads._get_session_pins("t4") == []


# ---------------------------------------------------------------------------
# Endpoints RPC
# ---------------------------------------------------------------------------


class TestThreadPinsEndpoints:
    async def test_set_and_get_via_rpc(self, fake_db):
        from backend.api.schemas import GetThreadPinsRequest, SetThreadPinsRequest

        with patch.object(threads, "_get_db", AsyncMock(return_value=fake_db)):
            set_resp = await threads.set_thread_pins(
                SetThreadPinsRequest(thread_id="t5", pins=["x.py", "x.py"])
            )
            get_resp = await threads.get_thread_pins(
                GetThreadPinsRequest(thread_id="t5")
            )
        assert set_resp.pins == ["x.py"]
        assert get_resp.thread_id == "t5"
        assert get_resp.pins == ["x.py"]

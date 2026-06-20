"""Sprint 8 — Modo Rotina: RoutineScheduler e CRUD de rotinas.

Verifica que:
- rotinas habilitadas são executadas quando next_run_at <= now
- rotinas desabilitadas são ignoradas pelo scheduler
- schedule_next calcula corretamente o próximo horário via cron
- CRUD de rotinas no DB funciona corretamente
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

# ---------------------------------------------------------------------------
# schedule_next
# ---------------------------------------------------------------------------


class TestScheduleNext:
    def test_returns_future_datetime(self) -> None:
        from backend.services.routines import schedule_next

        now = datetime.now(UTC)
        nxt = schedule_next("* * * * *", now)
        assert nxt > now

    def test_daily_at_midnight(self) -> None:
        from backend.services.routines import schedule_next

        base = datetime(2024, 1, 15, 23, 0, 0, tzinfo=UTC)
        nxt = schedule_next("0 0 * * *", base)
        assert nxt.hour == 0
        assert nxt.day == 16

    def test_invalid_cron_raises(self) -> None:
        from backend.services.routines import schedule_next

        with pytest.raises(ValueError):
            schedule_next("invalid cron", datetime.now(UTC))


# ---------------------------------------------------------------------------
# RoutineScheduler.tick
# ---------------------------------------------------------------------------


class TestRoutineSchedulerTick:
    @pytest.mark.asyncio
    async def test_enabled_due_routine_is_executed(self) -> None:
        from backend.services.routines import RoutineScheduler

        past = datetime.now(UTC) - timedelta(minutes=5)
        routine = MagicMock()
        routine.id = "r1"
        routine.enabled = True
        routine.next_run_at = past
        routine.instruction = "do something"
        routine.workspace_id = None

        executed: list[str] = []

        async def _fake_run(r: MagicMock) -> None:
            executed.append(r.id)

        scheduler = RoutineScheduler.__new__(RoutineScheduler)
        scheduler._run_routine = _fake_run

        async def _list_due() -> list[MagicMock]:
            return [routine]

        scheduler._list_due = _list_due
        await scheduler.tick()
        assert "r1" in executed

    @pytest.mark.asyncio
    async def test_disabled_routine_is_skipped(self) -> None:
        from backend.services.routines import RoutineScheduler

        past = datetime.now(UTC) - timedelta(minutes=5)
        routine = MagicMock()
        routine.id = "r2"
        routine.enabled = False
        routine.next_run_at = past

        executed: list[str] = []

        async def _fake_run(r: MagicMock) -> None:
            executed.append(r.id)

        scheduler = RoutineScheduler.__new__(RoutineScheduler)
        scheduler._run_routine = _fake_run

        async def _list_due() -> list[MagicMock]:
            return [routine]

        scheduler._list_due = _list_due
        await scheduler.tick()
        assert "r2" not in executed

    @pytest.mark.asyncio
    async def test_future_routine_is_skipped(self) -> None:
        from backend.services.routines import RoutineScheduler

        future = datetime.now(UTC) + timedelta(hours=1)
        routine = MagicMock()
        routine.id = "r3"
        routine.enabled = True
        routine.next_run_at = future

        executed: list[str] = []

        async def _fake_run(r: MagicMock) -> None:
            executed.append(r.id)

        scheduler = RoutineScheduler.__new__(RoutineScheduler)
        scheduler._run_routine = _fake_run

        async def _list_due() -> list[MagicMock]:
            return [routine]

        scheduler._list_due = _list_due
        await scheduler.tick()
        assert "r3" not in executed


# ---------------------------------------------------------------------------
# list_routines / create_routine
# ---------------------------------------------------------------------------


class TestRoutineCRUD:
    @pytest.mark.asyncio
    async def test_create_returns_routine_with_id(self, monkeypatch) -> None:
        from backend.services.routines import create_routine

        _ROW = {
            "id": "new-id",
            "user_id": 1,
            "name": "Minha rotina",
            "instruction": "faça X",
            "cron_expr": "0 9 * * *",
            "workspace_id": None,
            "enabled": 1,
            "last_run_at": None,
            "next_run_at": None,
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
        }

        mock_conn = AsyncMock()
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=None)
        mock_conn.execute = AsyncMock(return_value=AsyncMock(lastrowid=1))
        mock_conn.fetchone = AsyncMock(return_value=_ROW)
        mock_conn.commit = AsyncMock()

        import backend.services.routines as _mod

        monkeypatch.setattr(_mod, "_get_db", AsyncMock(return_value=mock_conn))

        routine = await create_routine(
            user_id=1,
            name="Minha rotina",
            instruction="faça X",
            cron_expr="0 9 * * *",
        )
        assert routine.id == "new-id"
        assert routine.name == "Minha rotina"

    @pytest.mark.asyncio
    async def test_list_routines_returns_list(self, monkeypatch) -> None:
        from backend.services.routines import list_routines

        _ROWS = [
            {
                "id": "r1",
                "user_id": 1,
                "name": "Diária",
                "instruction": "resume",
                "cron_expr": "0 8 * * *",
                "workspace_id": None,
                "enabled": 1,
                "last_run_at": None,
                "next_run_at": None,
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00",
            }
        ]

        mock_cursor = AsyncMock()
        mock_cursor.fetchall = AsyncMock(return_value=_ROWS)
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        import backend.services.routines as _mod

        monkeypatch.setattr(_mod, "_get_db", AsyncMock(return_value=mock_conn))

        routines = await list_routines(user_id=1)
        assert len(routines) == 1
        assert routines[0].id == "r1"

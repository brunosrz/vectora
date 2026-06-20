"""Modo Rotina — agendamento e execução automática de tarefas via cron.

RoutineScheduler roda como task asyncio no lifespan do servidor.
Tick a cada 60s: verifica rotinas com next_run_at <= now e as executa.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from croniter import croniter

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Modelos
# ---------------------------------------------------------------------------


@dataclass
class Routine:
    id: str
    user_id: int
    name: str
    instruction: str
    cron_expr: str
    workspace_id: str | None
    enabled: bool
    last_run_at: datetime | None
    next_run_at: datetime | None
    created_at: datetime
    updated_at: datetime


def _row_to_routine(row: dict[str, Any]) -> Routine:
    def _dt(v: str | None) -> datetime | None:
        if v is None:
            return None
        return datetime.fromisoformat(v).replace(tzinfo=UTC)

    return Routine(
        id=row["id"],
        user_id=row["user_id"],
        name=row["name"],
        instruction=row["instruction"],
        cron_expr=row["cron_expr"],
        workspace_id=row["workspace_id"],
        enabled=bool(row["enabled"]),
        last_run_at=_dt(row["last_run_at"]),
        next_run_at=_dt(row["next_run_at"]),
        created_at=datetime.fromisoformat(row["created_at"]).replace(tzinfo=UTC),
        updated_at=datetime.fromisoformat(row["updated_at"]).replace(tzinfo=UTC),
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def schedule_next(cron_expr: str, base: datetime) -> datetime:
    """Calcula o próximo datetime de execução após ``base``."""
    it = croniter(cron_expr, base)
    return it.get_next(datetime).replace(tzinfo=UTC)


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

_db_conn: Any = None


async def _get_db() -> Any:
    """Retorna conexão aiosqlite para rotinas (mesmo DB de auth)."""
    global _db_conn
    if _db_conn is not None:
        return _db_conn
    from pathlib import Path

    import aiosqlite

    db_path = Path.home() / ".vectora" / "checkpoints.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    _db_conn = await aiosqlite.connect(str(db_path))
    _db_conn.row_factory = aiosqlite.Row
    await _db_conn.execute("PRAGMA journal_mode=WAL")
    await _ensure_table(_db_conn)
    return _db_conn


async def _ensure_table(conn: Any) -> None:
    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS vectora_routines (
            id           TEXT PRIMARY KEY,
            user_id      INTEGER NOT NULL,
            name         TEXT NOT NULL,
            instruction  TEXT NOT NULL,
            cron_expr    TEXT NOT NULL,
            workspace_id TEXT,
            enabled      INTEGER NOT NULL DEFAULT 1,
            last_run_at  TEXT,
            next_run_at  TEXT,
            created_at   TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at   TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    await conn.commit()


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


async def create_routine(
    user_id: int,
    name: str,
    instruction: str,
    cron_expr: str,
    workspace_id: str | None = None,
) -> Routine:
    now = datetime.now(UTC)
    nxt = schedule_next(cron_expr, now)
    rid = str(uuid.uuid4())
    db = await _get_db()
    await db.execute(
        """
        INSERT INTO vectora_routines
          (id, user_id, name, instruction, cron_expr, workspace_id,
           enabled, next_run_at, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?, ?)
        """,
        (
            rid,
            user_id,
            name,
            instruction,
            cron_expr,
            workspace_id,
            nxt.isoformat(),
            now.isoformat(),
            now.isoformat(),
        ),
    )
    await db.commit()
    cursor = await db.execute("SELECT * FROM vectora_routines WHERE id = ?", (rid,))
    row = await cursor.fetchone()
    return _row_to_routine(dict(row))


async def list_routines(user_id: int) -> list[Routine]:
    db = await _get_db()
    cursor = await db.execute(
        "SELECT * FROM vectora_routines WHERE user_id = ? ORDER BY created_at",
        (user_id,),
    )
    rows = await cursor.fetchall()
    return [_row_to_routine(dict(r)) for r in rows]


async def update_routine(
    routine_id: str,
    user_id: int,
    *,
    enabled: bool | None = None,
    name: str | None = None,
    instruction: str | None = None,
    cron_expr: str | None = None,
) -> Routine | None:
    db = await _get_db()
    cursor = await db.execute(
        "SELECT * FROM vectora_routines WHERE id = ? AND user_id = ?",
        (routine_id, user_id),
    )
    row = await cursor.fetchone()
    if row is None:
        return None
    current = _row_to_routine(dict(row))
    new_enabled = enabled if enabled is not None else current.enabled
    new_name = name or current.name
    new_instruction = instruction or current.instruction
    new_cron = cron_expr or current.cron_expr
    now = datetime.now(UTC)
    nxt = schedule_next(new_cron, now)
    await db.execute(
        """
        UPDATE vectora_routines
           SET enabled=?, name=?, instruction=?, cron_expr=?,
               next_run_at=?, updated_at=?
         WHERE id=? AND user_id=?
        """,
        (
            int(new_enabled),
            new_name,
            new_instruction,
            new_cron,
            nxt.isoformat(),
            now.isoformat(),
            routine_id,
            user_id,
        ),
    )
    await db.commit()
    cursor2 = await db.execute(
        "SELECT * FROM vectora_routines WHERE id = ?", (routine_id,)
    )
    row2 = await cursor2.fetchone()
    return _row_to_routine(dict(row2))


async def delete_routine(routine_id: str, user_id: int) -> bool:
    db = await _get_db()
    cursor = await db.execute(
        "DELETE FROM vectora_routines WHERE id = ? AND user_id = ?",
        (routine_id, user_id),
    )
    await db.commit()
    return cursor.rowcount > 0


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------


class RoutineScheduler:
    """Executa rotinas cujo next_run_at <= now() a cada tick."""

    def __init__(self) -> None:
        self._task: asyncio.Task[None] | None = None

    async def _list_due(self) -> list[Routine]:
        db = await _get_db()
        now_iso = datetime.now(UTC).isoformat()
        cursor = await db.execute(
            """
            SELECT * FROM vectora_routines
             WHERE enabled = 1
               AND next_run_at IS NOT NULL
               AND next_run_at <= ?
            """,
            (now_iso,),
        )
        rows = await cursor.fetchall()
        return [_row_to_routine(dict(r)) for r in rows]

    async def _run_routine(self, routine: Routine) -> None:
        try:
            from backend.services.agent_factory import get_user_agent

            logger.info(
                "routines: executando rotina",
                extra={"id": routine.id, "routine_name": routine.name},
            )
            now = datetime.now(UTC)
            nxt = schedule_next(routine.cron_expr, now)
            db = await _get_db()
            await db.execute(
                "UPDATE vectora_routines SET last_run_at=?, next_run_at=? WHERE id=?",
                (now.isoformat(), nxt.isoformat(), routine.id),
            )
            await db.commit()

            agent = await get_user_agent(user_id=str(routine.user_id))
            thread_id = f"routine-{routine.id}-{now.strftime('%Y%m%dT%H%M%S')}"
            await agent.ainvoke(
                {"messages": [{"role": "user", "content": routine.instruction}]},
                config={"configurable": {"thread_id": thread_id}},
            )
        except Exception:
            logger.exception(
                "routines: falha ao executar rotina",
                extra={"id": routine.id},
            )

    async def tick(self) -> None:
        due = await self._list_due()
        for routine in due:
            if not routine.enabled:
                continue
            now = datetime.now(UTC)
            if routine.next_run_at is None or routine.next_run_at > now:
                continue
            await self._run_routine(routine)

    async def _loop(self, interval: int = 60) -> None:
        while True:
            try:
                await self.tick()
            except Exception:
                logger.exception("routines: erro no tick do scheduler")
            await asyncio.sleep(interval)

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._loop())

    def stop(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()


_scheduler: RoutineScheduler | None = None


def get_scheduler() -> RoutineScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = RoutineScheduler()
    return _scheduler

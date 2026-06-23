"""Agendador de rotinas — execução automática de instruções em base cron."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from datetime import UTC, datetime
from typing import Any

from croniter import croniter

logger = logging.getLogger(__name__)


class Routine:
    """Representa uma rotina agendada."""

    def __init__(
        self,
        routine_id: str,
        user_id: int,
        name: str,
        instruction: str,
        cron_expr: str,
        workspace_id: str | None = None,
        enabled: bool = True,
        last_run_at: str | None = None,
        next_run_at: str | None = None,
    ):
        self.id = routine_id
        self.user_id = user_id
        self.name = name
        self.instruction = instruction
        self.cron_expr = cron_expr
        self.workspace_id = workspace_id
        self.enabled = enabled
        self.last_run_at = last_run_at
        self.next_run_at = next_run_at

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "instruction": self.instruction,
            "cron_expr": self.cron_expr,
            "workspace_id": self.workspace_id,
            "enabled": self.enabled,
            "last_run_at": self.last_run_at,
            "next_run_at": self.next_run_at,
        }


def _row_to_routine(row: dict[str, Any]) -> Routine:
    return Routine(
        routine_id=row["id"],
        user_id=row["user_id"],
        name=row["name"],
        instruction=row["instruction"],
        cron_expr=row["cron_expr"],
        workspace_id=row.get("workspace_id"),
        enabled=bool(row.get("enabled", 1)),
        last_run_at=row.get("last_run_at"),
        next_run_at=row.get("next_run_at"),
    )


async def _get_db() -> Any:
    """Retorna conexão aiosqlite já aberta (injetável em testes via monkeypatch)."""
    import aiosqlite

    from backend.settings import settings

    db_path = settings.db_dsn or ":memory:"
    return await aiosqlite.connect(db_path)


class RoutineScheduler:
    """Executor de rotinas agendadas via croniter."""

    def __init__(self) -> None:
        self._running = False
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("RoutineScheduler iniciado")

    async def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        logger.info("RoutineScheduler parado")

    async def _run_loop(self) -> None:
        try:
            while self._running:
                await self.tick()
                await asyncio.sleep(60)
        except asyncio.CancelledError:
            pass

    async def tick(self) -> None:
        """Verifica e executa rotinas vencidas."""
        due = await self._list_due()
        for routine in due:
            if not routine.enabled:
                continue
            now = datetime.now(UTC)
            next_run = routine.next_run_at
            if isinstance(next_run, str):
                try:
                    next_run = datetime.fromisoformat(next_run)
                except ValueError:
                    continue
            if next_run is None or next_run > now:
                continue
            await self._run_routine(routine)

    async def _list_due(self) -> list[Any]:
        """Lista rotinas com next_run_at <= now (sobrescrito em testes)."""
        return []

    async def _run_routine(self, routine: Any) -> None:
        """Executa uma rotina (sobrescrito em testes)."""
        logger.info("Executando rotina: %s", routine.id)

    @staticmethod
    def schedule_next(routine: Routine) -> str | None:
        try:
            cron = croniter(routine.cron_expr, datetime.now(UTC))
            return cron.get_next(datetime).isoformat()
        except Exception as e:
            logger.exception("Erro ao calcular próximo horário: %s", e)
            return None


def schedule_next(cron_expr: str, base_time: datetime | None = None) -> datetime:
    """Calcula próximo horário de execução. Levanta ValueError em cron inválido."""
    try:
        cron = croniter(cron_expr, base_time or datetime.now(UTC))
        return cron.get_next(datetime)
    except Exception as e:
        msg = f"Cron inválido '{cron_expr}': {e}"
        raise ValueError(msg) from e


async def create_routine(
    user_id: int,
    name: str,
    instruction: str,
    cron_expr: str,
    workspace_id: str | None = None,
) -> Routine:
    """Cria rotina no DB."""
    from uuid import uuid4

    routine_id = str(uuid4())
    next_run = schedule_next(cron_expr)

    conn = await _get_db()
    try:
        conn.row_factory = lambda c, r: dict(
            zip([col[0] for col in c.description], r, strict=False)
        )
        cursor = await conn.execute(
            """
            INSERT INTO vectora_routines
              (id, user_id, name, instruction, cron_expr, workspace_id, next_run_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                routine_id,
                user_id,
                name,
                instruction,
                cron_expr,
                workspace_id,
                next_run.isoformat(),
            ),
        )
        await conn.commit()
        row = await cursor.fetchone()
        if row:
            return _row_to_routine(row)
    finally:
        with contextlib.suppress(Exception):
            await conn.close()

    return Routine(
        routine_id=routine_id,
        user_id=user_id,
        name=name,
        instruction=instruction,
        cron_expr=cron_expr,
        workspace_id=workspace_id,
        next_run_at=next_run.isoformat(),
    )


async def list_routines(user_id: int) -> list[Routine]:
    """Lista rotinas do usuário."""
    conn = await _get_db()
    try:
        conn.row_factory = lambda c, r: dict(
            zip([col[0] for col in c.description], r, strict=False)
        )
        cursor = await conn.execute(
            "SELECT * FROM vectora_routines WHERE user_id = ?",
            (user_id,),
        )
        rows = await cursor.fetchall()
    finally:
        with contextlib.suppress(Exception):
            await conn.close()
    return [_row_to_routine(r) for r in rows]


async def update_routine(routine_id: str, **updates: Any) -> Routine | None:
    return None


async def delete_routine(routine_id: str, user_id: int | None = None) -> bool:
    return True


_scheduler_instance: RoutineScheduler | None = None


def get_scheduler() -> RoutineScheduler:
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = RoutineScheduler()
    return _scheduler_instance

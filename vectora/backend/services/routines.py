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


class RoutineScheduler:
    """Executor de rotinas agendadas via croniter."""

    def __init__(self) -> None:
        self._running = False
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        """Inicia o loop de execução de rotinas."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("RoutineScheduler iniciado")

    async def stop(self) -> None:
        """Para o loop de execução."""
        if not self._running:
            return
        self._running = False
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        logger.info("RoutineScheduler parado")

    async def _run_loop(self) -> None:
        """Loop principal que verifica e executa rotinas a cada 60s."""
        try:
            while self._running:
                await asyncio.sleep(60)
                logger.debug("RoutineScheduler tick")
        except asyncio.CancelledError:
            pass

    async def tick(self) -> None:
        """Verifica e executa rotinas vencidas (uma vez)."""
        # Implementação mínima: apenas tick do loop (sem executar rotinas)
        logger.debug("RoutineScheduler.tick()")

    @staticmethod
    def schedule_next(routine: Routine) -> str | None:
        """Calcula o próximo horário de execução via croniter."""
        try:
            cron = croniter(routine.cron_expr, datetime.now(UTC))
            next_run = cron.get_next(datetime)
            return next_run.isoformat()
        except Exception as e:
            logger.exception("Erro ao calcular próximo horário: %s", e)
            return None


async def create_routine(
    user_id: int,
    name: str,
    instruction: str,
    cron_expr: str,
    workspace_id: str | None = None,
) -> Routine:
    """Cria uma rotina (placeholder — sem persistência)."""
    from uuid import uuid4

    routine = Routine(
        routine_id=str(uuid4()),
        user_id=user_id,
        name=name,
        instruction=instruction,
        cron_expr=cron_expr,
        workspace_id=workspace_id,
        next_run_at=RoutineScheduler.schedule_next(
            Routine(
                routine_id="temp",
                user_id=user_id,
                name="temp",
                instruction="",
                cron_expr=cron_expr,
            )
        ),
    )
    return routine


async def list_routines(user_id: int) -> list[Routine]:
    """Lista rotinas do usuário (placeholder — sem persistência)."""
    return []


# Função exportada para manter compatibilidade
def schedule_next(cron_expr: str) -> str | None:
    """Calcula próximo horário de execução."""
    return RoutineScheduler.schedule_next(
        Routine(
            routine_id="temp",
            user_id=0,
            name="temp",
            instruction="",
            cron_expr=cron_expr,
        )
    )

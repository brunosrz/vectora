"""Heartbreak — escuta contínua sem input do usuário (modo autônomo)."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)


class HeartbreakSession:
    """Representa uma sessão Heartbreak em execução."""

    def __init__(
        self,
        session_id: str,
        user_id: int,
        workspace_id: str,
        instruction: str,
        status: str = "active",
    ):
        self.session_id = session_id
        self.user_id = user_id
        self.workspace_id = workspace_id
        self.instruction = instruction
        self.status = status
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        """Inicia a sessão Heartbreak (placeholder)."""
        self._task = asyncio.create_task(self._run())
        logger.info("HeartbreakSession iniciada: %s", self.session_id)

    async def stop(self) -> None:
        """Para a sessão Heartbreak."""
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self.status = "inactive"
        logger.info("HeartbreakSession parada: %s", self.session_id)

    async def _run(self) -> None:
        """Loop principal (placeholder — sem lógica real)."""
        try:
            while self.status == "active":
                await asyncio.sleep(60)
                logger.debug("HeartbreakSession tick: %s", self.session_id)
        except asyncio.CancelledError:
            pass


class HeartbreakController:
    """Controla múltiplas sessões Heartbreak (placeholder)."""

    def __init__(self):
        self._sessions: dict[str, HeartbreakSession] = {}

    async def create_session(
        self, session_id: str, user_id: int, workspace_id: str, instruction: str
    ) -> HeartbreakSession:
        """Cria e inicia uma sessão Heartbreak."""
        session = HeartbreakSession(session_id, user_id, workspace_id, instruction)
        await session.start()
        self._sessions[session_id] = session
        return session

    async def delete_session(self, session_id: str) -> bool:
        """Para e remove uma sessão."""
        if session_id in self._sessions:
            await self._sessions[session_id].stop()
            del self._sessions[session_id]
            return True
        return False

    def list_sessions(self, user_id: int) -> list[HeartbreakSession]:
        """Lista sessões ativas do usuário."""
        return [s for s in self._sessions.values() if s.user_id == user_id]


_controller: HeartbreakController | None = None


def get_controller() -> HeartbreakController:
    """Retorna instância global do Heartbreak controller."""
    global _controller
    if _controller is None:
        _controller = HeartbreakController()
    return _controller

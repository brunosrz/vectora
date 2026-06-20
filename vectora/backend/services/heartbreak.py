"""Modo Heartbreak — agente de escuta contínua sem input manual.

Cada HeartbreakSession fica "acordada", esperando eventos externos
(webhook POST ou tick de intervalo). Cada evento cria uma thread efêmera
e dispara o agente com o payload como contexto.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import uuid
from collections.abc import Callable, Coroutine
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)

_VALID_TRIGGERS = {"webhook", "interval"}


async def _default_run_event(
    session: HeartbreakSession,
    payload: dict[str, Any],
) -> None:
    from backend.services.agent_factory import get_user_agent

    agent = await get_user_agent(user_id=str(session.user_id))
    thread_id = f"hb-{session.id}-{uuid.uuid4().hex[:8]}"
    context = f"Evento recebido: {payload}\n\nInstrução: {session.instruction}"
    await agent.ainvoke(
        {"messages": [{"role": "user", "content": context}]},
        config={"configurable": {"thread_id": thread_id}},
    )


class HeartbreakSession:
    """Sessão de escuta contínua de um usuário."""

    def __init__(
        self,
        user_id: int,
        instruction: str,
        workspace_id: str | None,
    ) -> None:
        self.id = str(uuid.uuid4())
        self.user_id = user_id
        self.instruction = instruction
        self.workspace_id = workspace_id
        self.status = "active"
        self.triggers: list[dict[str, Any]] = []
        self.run_count = 0
        self._running = False
        self._interval_task: asyncio.Task[None] | None = None
        self.created_at = datetime.now(UTC)
        # Stored as a Callable attribute so tests can replace it without method-assign.
        self._run_event: Callable[
            [HeartbreakSession, dict[str, Any]],
            Coroutine[Any, Any, None],
        ] = _default_run_event

    def register_trigger(self, trigger_type: str, config: dict[str, Any]) -> None:
        if trigger_type not in _VALID_TRIGGERS:
            raise ValueError(
                f"Tipo de trigger inválido: {trigger_type!r}. Use: {_VALID_TRIGGERS}"
            )
        self.triggers.append({"type": trigger_type, "config": config})
        if trigger_type == "interval" and not self._running:
            seconds = int(config.get("seconds", 60))
            self._running = True
            with contextlib.suppress(RuntimeError):
                self._interval_task = asyncio.create_task(self._interval_loop(seconds))

    async def _interval_loop(self, seconds: int) -> None:
        while self._running:
            await asyncio.sleep(seconds)
            if not self._running:
                break
            await self.send_event(
                {"trigger": "interval", "ts": datetime.now(UTC).isoformat()}
            )

    async def send_event(self, payload: dict[str, Any]) -> None:
        """Processa um evento externo na sessão."""
        try:
            await self._run_event(self, payload)
            self.run_count += 1
        except Exception:
            logger.exception(
                "heartbreak: falha ao processar evento",
                extra={"session_id": self.id},
            )

    def stop(self) -> None:
        self._running = False
        self.status = "stopped"
        if self._interval_task and not self._interval_task.done():
            self._interval_task.cancel()


class HeartbreakManager:
    """Gerencia sessões Heartbreak ativas em memória."""

    def __init__(self) -> None:
        self._sessions: dict[str, HeartbreakSession] = {}

    def create(
        self,
        user_id: int,
        instruction: str,
        workspace_id: str | None = None,
    ) -> HeartbreakSession:
        session = HeartbreakSession(
            user_id=user_id,
            instruction=instruction,
            workspace_id=workspace_id,
        )
        self._sessions[session.id] = session
        return session

    def get(self, session_id: str) -> HeartbreakSession | None:
        return self._sessions.get(session_id)

    def list_active(self, user_id: int | None = None) -> list[HeartbreakSession]:
        sessions = [s for s in self._sessions.values() if s.status == "active"]
        if user_id is not None:
            sessions = [s for s in sessions if s.user_id == user_id]
        return sessions

    def stop(self, session_id: str) -> bool:
        session = self._sessions.get(session_id)
        if session is None:
            return False
        session.stop()
        del self._sessions[session_id]
        return True

    @property
    def active_count(self) -> int:
        return sum(1 for s in self._sessions.values() if s.status == "active")


_manager: HeartbreakManager | None = None


def get_manager() -> HeartbreakManager:
    global _manager
    if _manager is None:
        _manager = HeartbreakManager()
    return _manager

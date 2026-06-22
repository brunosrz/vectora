"""Heartbreak — escuta contínua sem input do usuário (modo autônomo)."""

from __future__ import annotations

import contextlib
import asyncio
import logging
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

_VALID_TRIGGERS = {"webhook", "interval"}


class HeartbreakSession:
    """Sessão Heartbreak: aguarda eventos externos e despacha agente."""

    def __init__(
        self,
        user_id: int,
        instruction: str,
        workspace_id: str | None = None,
    ):
        self.id = str(uuid4())
        self.user_id = user_id
        self.instruction = instruction
        self.workspace_id = workspace_id
        self.status = "active"
        self._running = False
        self.triggers: list[dict[str, Any]] = []
        self.run_count = 0

    def register_trigger(self, trigger_type: str, config: dict[str, Any]) -> None:
        """Registra um trigger (webhook ou interval)."""
        if trigger_type not in _VALID_TRIGGERS:
            msg = f"Trigger desconhecido: {trigger_type!r}. Válidos: {_VALID_TRIGGERS}"
            raise ValueError(msg)
        self.triggers.append({"type": trigger_type, "config": config})

    async def send_event(self, payload: dict[str, Any]) -> None:
        """Recebe evento externo e executa o agente."""
        try:
            await self._run_event(self, payload)
            self.run_count += 1
        except Exception as e:
            logger.exception("Erro ao processar evento na sessão %s: %s", self.id, e)

    async def _run_event(self, session: HeartbreakSession, payload: dict[str, Any]) -> None:
        """Lógica padrão (pode ser substituída em testes)."""
        logger.info("HeartbreakSession.run_event: session=%s payload=%s", session.id, payload)


class HeartbreakManager:
    """Gerencia múltiplas sessões Heartbreak."""

    def __init__(self) -> None:
        self._sessions: dict[str, HeartbreakSession] = {}

    def create(
        self,
        user_id: int,
        instruction: str,
        workspace_id: str | None = None,
    ) -> HeartbreakSession:
        """Cria e registra uma nova sessão."""
        session = HeartbreakSession(user_id=user_id, instruction=instruction, workspace_id=workspace_id)
        self._sessions[session.id] = session
        return session

    def stop(self, session_id: str) -> bool:
        """Para e remove uma sessão. Retorna False se não existia."""
        if session_id not in self._sessions:
            return False
        session = self._sessions.pop(session_id)
        session.status = "inactive"
        return True

    def list_active(self, user_id: int) -> list[HeartbreakSession]:
        """Lista sessões ativas do usuário."""
        return [s for s in self._sessions.values() if s.user_id == user_id and s.status == "active"]


_manager: HeartbreakManager | None = None


def get_manager() -> HeartbreakManager:
    """Retorna instância global do HeartbreakManager."""
    global _manager
    if _manager is None:
        _manager = HeartbreakManager()
    return _manager

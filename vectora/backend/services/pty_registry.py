"""Registry de sessões PTY ativas.

Singleton ``pty_registry`` keyed por ``terminal_id``. A unicidade do id é
responsabilidade do criador (handler WS gera UUID curto). Múltiplas sessões
por thread/workspace são permitidas (cada split é uma sessão própria).
"""

from __future__ import annotations

import logging

from backend.services.pty_session import PtySession

logger = logging.getLogger(__name__)


class PtyRegistry:
    """Mantém as sessões PTY vivas em memória do processo."""

    def __init__(self) -> None:
        self._sessions: dict[str, PtySession] = {}

    def add(self, session: PtySession) -> None:
        self._sessions[session.terminal_id] = session

    def get(self, terminal_id: str) -> PtySession | None:
        return self._sessions.get(terminal_id)

    def list_for_thread(self, thread_id: str) -> list[PtySession]:
        return [s for s in self._sessions.values() if s.thread_id == thread_id]

    def close(self, terminal_id: str) -> bool:
        session = self._sessions.pop(terminal_id, None)
        if session is None:
            return False
        session.close()
        return True

    def close_all(self) -> None:
        """Encerra todas as PTYs — chamado no shutdown do servidor."""
        for sid in list(self._sessions.keys()):
            try:
                self._sessions[sid].close()
            except Exception:
                logger.debug("pty_registry: erro ao encerrar %s", sid)
        self._sessions.clear()


#: Instância global usada pelo handler WS e pelo lifespan do servidor.
pty_registry: PtyRegistry = PtyRegistry()

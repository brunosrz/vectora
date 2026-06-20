"""Sprint 9 — Modo Heartbreak: sessões de escuta contínua event-driven.

Cobre caminho feliz + erro para:
- criar sessão
- registrar trigger webhook/interval
- EventLoop: recebe evento e chama agente
- encerrar sessão (stop)
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# HeartbreakSession
# ---------------------------------------------------------------------------


class TestHeartbreakSession:
    def test_create_session_has_id(self) -> None:
        from backend.services.heartbreak import HeartbreakSession

        session = HeartbreakSession(
            user_id=1,
            instruction="monitore X",
            workspace_id=None,
        )
        assert session.id
        assert session.status == "active"
        assert session.user_id == 1

    def test_session_starts_inactive(self) -> None:
        from backend.services.heartbreak import HeartbreakSession

        session = HeartbreakSession(
            user_id=2,
            instruction="faça Y",
            workspace_id=None,
        )
        assert not session._running


# ---------------------------------------------------------------------------
# register_trigger
# ---------------------------------------------------------------------------


class TestRegisterTrigger:
    def test_webhook_trigger_registered(self) -> None:
        from backend.services.heartbreak import HeartbreakSession

        session = HeartbreakSession(user_id=1, instruction="ok", workspace_id=None)
        session.register_trigger("webhook", {})
        assert any(t["type"] == "webhook" for t in session.triggers)

    def test_interval_trigger_registered(self) -> None:
        from backend.services.heartbreak import HeartbreakSession

        session = HeartbreakSession(user_id=1, instruction="ok", workspace_id=None)
        session.register_trigger("interval", {"seconds": 60})
        assert any(t["type"] == "interval" for t in session.triggers)

    def test_unknown_trigger_raises(self) -> None:
        from backend.services.heartbreak import HeartbreakSession

        session = HeartbreakSession(user_id=1, instruction="ok", workspace_id=None)
        with pytest.raises(ValueError):
            session.register_trigger("email", {})


# ---------------------------------------------------------------------------
# EventLoop: send_event
# ---------------------------------------------------------------------------


class TestSendEvent:
    @pytest.mark.asyncio
    async def test_send_event_calls_agent(self) -> None:
        from backend.services.heartbreak import HeartbreakSession

        called: list[str] = []

        async def _fake_run(session: HeartbreakSession, payload: dict) -> None:
            called.append(session.id)

        session = HeartbreakSession(user_id=1, instruction="monit", workspace_id=None)
        session._run_event = _fake_run  # type: ignore[method-assign]

        await session.send_event({"data": "ping"})
        assert session.id in called

    @pytest.mark.asyncio
    async def test_send_event_logs_on_error(self) -> None:
        from backend.services.heartbreak import HeartbreakSession

        async def _fail(session: HeartbreakSession, payload: dict) -> None:
            raise RuntimeError("boom")

        session = HeartbreakSession(user_id=1, instruction="monit", workspace_id=None)
        session._run_event = _fail  # type: ignore[method-assign]

        await session.send_event({"data": "ping"})
        assert session.run_count == 0


# ---------------------------------------------------------------------------
# HeartbreakManager: create / list / stop
# ---------------------------------------------------------------------------


class TestHeartbreakManager:
    def test_create_and_list(self) -> None:
        from backend.services.heartbreak import HeartbreakManager

        mgr = HeartbreakManager()
        session = mgr.create(user_id=1, instruction="test", workspace_id=None)
        sessions = mgr.list_active(user_id=1)
        assert any(s.id == session.id for s in sessions)

    def test_stop_removes_from_active(self) -> None:
        from backend.services.heartbreak import HeartbreakManager

        mgr = HeartbreakManager()
        session = mgr.create(user_id=1, instruction="test", workspace_id=None)
        mgr.stop(session.id)
        sessions = mgr.list_active(user_id=1)
        assert not any(s.id == session.id for s in sessions)

    def test_stop_nonexistent_returns_false(self) -> None:
        from backend.services.heartbreak import HeartbreakManager

        mgr = HeartbreakManager()
        assert mgr.stop("does-not-exist") is False

    def test_list_active_filters_by_user(self) -> None:
        from backend.services.heartbreak import HeartbreakManager

        mgr = HeartbreakManager()
        mgr.create(user_id=1, instruction="u1", workspace_id=None)
        mgr.create(user_id=2, instruction="u2", workspace_id=None)
        assert len(mgr.list_active(user_id=1)) == 1
        assert len(mgr.list_active(user_id=2)) == 1

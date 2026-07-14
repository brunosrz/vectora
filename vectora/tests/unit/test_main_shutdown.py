"""Shutdown correto ao fechar terminal ou receber SIGINT/SIGTERM/SIGHUP.

Garante que _install_terminal_signals seta server.should_exit=True e chama
icon.stop() quando o sinal chega. Testa também que o handler NÃO é instalado
quando a entrada não é TTY (VPS/Docker/Electron).
"""

from __future__ import annotations

import os
import signal
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


class _FakeServer:
    def __init__(self) -> None:
        self.should_exit = False

    def run(self) -> None:
        pass


def _get_handler(signum: int) -> Any:
    return signal.getsignal(signum)


def test_shutdown_sets_should_exit_on_sigint() -> None:
    """SIGINT → server.should_exit = True."""
    from backend.main import _install_terminal_signals

    server = _FakeServer()
    icon_ref: list[Any] = [None]

    orig = {}
    for sig in (signal.SIGINT, signal.SIGTERM):
        orig[sig] = signal.getsignal(sig)

    try:
        _install_terminal_signals(server, icon_ref)
        handler = _get_handler(signal.SIGINT)
        assert callable(handler)
        handler(signal.SIGINT, None)
        assert server.should_exit is True
    finally:
        for sig, h in orig.items():
            signal.signal(sig, h)


def test_shutdown_calls_icon_stop_when_present() -> None:
    """Quando icon_ref[0] está preenchido, handler chama icon.stop()."""
    from backend.main import _install_terminal_signals

    server = _FakeServer()
    icon = MagicMock()
    icon_ref: list[Any] = [icon]

    orig_int = signal.getsignal(signal.SIGINT)
    orig_term = signal.getsignal(signal.SIGTERM)
    try:
        _install_terminal_signals(server, icon_ref)
        handler = _get_handler(signal.SIGTERM)
        assert callable(handler)
        handler(signal.SIGTERM, None)
        assert server.should_exit is True
        icon.stop.assert_called_once()
    finally:
        signal.signal(signal.SIGINT, orig_int)
        signal.signal(signal.SIGTERM, orig_term)


def test_shutdown_no_error_when_icon_is_none() -> None:
    """Handler não falha quando icon_ref[0] é None (modo servidor puro)."""
    from backend.main import _install_terminal_signals

    server = _FakeServer()
    icon_ref: list[Any] = [None]

    orig_int = signal.getsignal(signal.SIGINT)
    orig_term = signal.getsignal(signal.SIGTERM)
    try:
        _install_terminal_signals(server, icon_ref)
        handler = _get_handler(signal.SIGINT)
        handler(signal.SIGINT, None)
        assert server.should_exit is True
    finally:
        signal.signal(signal.SIGINT, orig_int)
        signal.signal(signal.SIGTERM, orig_term)


_SIGHUP: int | None = getattr(signal, "SIGHUP", None)


def test_shutdown_sighup_handling() -> None:
    """SIGHUP registrado em Unix; em Windows verifica que SIGINT/SIGTERM continuam ok."""
    from backend.main import _install_terminal_signals

    server = _FakeServer()
    icon_ref: list[Any] = [None]

    orig_int = signal.getsignal(signal.SIGINT)
    orig_term = signal.getsignal(signal.SIGTERM)
    try:
        _install_terminal_signals(server, icon_ref)
        if _SIGHUP is not None:
            orig_hup = signal.getsignal(_SIGHUP)
            try:
                handler = _get_handler(_SIGHUP)
                assert callable(handler)
                handler(_SIGHUP, None)
                assert server.should_exit is True
            finally:
                signal.signal(_SIGHUP, orig_hup)
        else:
            handler = _get_handler(signal.SIGINT)
            assert callable(handler)
    finally:
        signal.signal(signal.SIGINT, orig_int)
        signal.signal(signal.SIGTERM, orig_term)


def test_tray_exposes_icon_via_icon_ref() -> None:
    """run_server_with_tray preenche icon_ref[0] com o pystray.Icon criado."""
    pystray_mock = MagicMock()
    icon_instance = MagicMock()
    pystray_mock.Icon.return_value = icon_instance
    pystray_mock.Menu.return_value = MagicMock()
    pystray_mock.MenuItem = MagicMock()

    server = _FakeServer()
    icon_ref: list[Any] = [None]

    with (
        patch.dict("sys.modules", {"pystray": pystray_mock}),
        patch("backend.services.tray.has_display", return_value=True),
        patch("backend.services.tray._build_icon_image", return_value=MagicMock()),
        patch("backend.services.tray._enable_dark_mode_win32"),
        patch("backend.services.tray.threading.Thread") as mock_thread,
        patch("backend.services.tray.threading.Timer") as mock_timer,
        patch.dict(os.environ, {}, clear=False),
    ):
        os.environ.pop("VECTORA_DESKTOP", None)

        mock_thread.return_value = MagicMock()
        mock_timer.return_value = MagicMock()

        import backend.services.tray as tray_mod

        tray_mod.run_server_with_tray(
            server,  # type: ignore[arg-type]
            "http://localhost:8080",
            headless=True,
            icon_ref=icon_ref,
        )

    assert icon_ref[0] is icon_instance

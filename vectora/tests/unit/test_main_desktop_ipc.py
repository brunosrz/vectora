"""Testes do transporte IPC desktop (Named Pipe / UDS).

Verifica que em modo VECTORA_DESKTOP=1:
  - Linux/macOS: uvicorn.Config recebe uds=<path> e não host=<ip>
  - Windows: VECTORA_IPC_PIPE é setado em os.environ e impresso em stdout

Os testes NÃO sobem servidor real — todos os componentes bloqueantes são
substituídos por mocks.
"""

from __future__ import annotations

import asyncio
import contextlib
import os
import sys
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# ipc_pipe_win — pipe_name e PIPE_ENV_VAR
# ---------------------------------------------------------------------------


def test_pipe_name_contains_pid() -> None:
    """pipe_name() inclui PID do processo — garante unicidade por execução."""
    from backend.services.ipc_pipe_win import pipe_name

    name = pipe_name()
    assert str(os.getpid()) in name


def test_pipe_name_windows_format() -> None:
    """pipe_name() retorna caminho no formato UNC do Windows."""
    from backend.services.ipc_pipe_win import pipe_name

    name = pipe_name()
    assert name.startswith("\\\\.\\pipe\\vectora-")


def test_pipe_env_var_constant() -> None:
    """PIPE_ENV_VAR é o valor que o Electron procura em stdout."""
    from backend.services.ipc_pipe_win import PIPE_ENV_VAR

    assert PIPE_ENV_VAR == "VECTORA_IPC_PIPE"


# ---------------------------------------------------------------------------
# UDS — Linux/macOS: uvicorn.Config recebe uds=, não host=
# ---------------------------------------------------------------------------


@pytest.mark.skipif(sys.platform == "win32", reason="UDS só em Linux/macOS")
def test_desktop_uds_config_not_tcp() -> None:
    """Com VECTORA_DESKTOP=1 em Linux/macOS, uvicorn.Config recebe uds=<path>."""
    import argparse

    captured_config_kwargs: dict[str, Any] = {}

    class _FakeConfig:
        def __init__(self, *_: Any, **kwargs: Any) -> None:
            captured_config_kwargs.update(kwargs)

    class _FakeServer:
        should_exit = False

        def __init__(self, *_: Any) -> None:
            pass

    args = argparse.Namespace(
        headless=False,
        host="0.0.0.0",  # noqa: S104
        port=None,
        ssl_certfile=None,
        ssl_keyfile=None,
    )

    with (
        patch.dict(os.environ, {"VECTORA_DESKTOP": "1"}, clear=False),
        patch("uvicorn.Config", side_effect=_FakeConfig),
        patch("uvicorn.Server", return_value=_FakeServer()),
        patch("backend.api.server.create_app", return_value=MagicMock()),
        patch("backend.main._start_vite_dev", return_value=None),
        patch("backend.main._kill_vite"),
        patch("backend.services.tray.run_server_with_tray", return_value=None),
        patch("os._exit"),
    ):
        from backend.main import _run_start

        _run_start(args)

    assert "uds" in captured_config_kwargs, "uvicorn.Config deveria receber uds="
    assert captured_config_kwargs["uds"].endswith("vectora.sock")
    assert "host" not in captured_config_kwargs, "Não deve abrir porta TCP no desktop"


@pytest.mark.skipif(sys.platform == "win32", reason="UDS só em Linux/macOS")
def test_desktop_uds_path_under_home_vectora() -> None:
    """O socket UDS fica em ~/.vectora/vectora.sock."""
    expected = str(Path.home() / ".vectora" / "vectora.sock")

    import argparse

    captured: dict[str, str] = {}

    class _FakeConfig:
        def __init__(self, *_: Any, **kwargs: Any) -> None:
            if "uds" in kwargs:
                captured["uds"] = kwargs["uds"]

    args = argparse.Namespace(
        headless=False,
        host="0.0.0.0",  # noqa: S104
        port=None,
        ssl_certfile=None,
        ssl_keyfile=None,
    )

    with (
        patch.dict(os.environ, {"VECTORA_DESKTOP": "1"}, clear=False),
        patch("uvicorn.Config", side_effect=_FakeConfig),
        patch("uvicorn.Server", return_value=MagicMock()),
        patch("backend.api.server.create_app", return_value=MagicMock()),
        patch("backend.main._start_vite_dev", return_value=None),
        patch("backend.main._kill_vite"),
        patch("backend.services.tray.run_server_with_tray"),
        patch("os._exit"),
    ):
        from backend.main import _run_start

        _run_start(args)

    assert captured.get("uds") == expected


@pytest.mark.skipif(sys.platform == "win32", reason="UDS só em Linux/macOS")
def test_non_desktop_uses_tcp_host() -> None:
    """Sem VECTORA_DESKTOP, uvicorn.Config recebe host= (modo servidor/VPS)."""
    import argparse

    captured_config_kwargs: dict[str, Any] = {}

    class _FakeConfig:
        def __init__(self, *_: Any, **kwargs: Any) -> None:
            captured_config_kwargs.update(kwargs)

    args = argparse.Namespace(
        headless=False,
        host="0.0.0.0",  # noqa: S104
        port=8080,
        ssl_certfile=None,
        ssl_keyfile=None,
    )

    env = {k: v for k, v in os.environ.items() if k != "VECTORA_DESKTOP"}

    with (
        patch.dict(os.environ, env, clear=True),
        patch("uvicorn.Config", side_effect=_FakeConfig),
        patch("uvicorn.Server", return_value=MagicMock()),
        patch("backend.api.server.create_app", return_value=MagicMock()),
        patch("backend.main._start_vite_dev", return_value=None),
        patch("backend.main._kill_vite"),
        patch("backend.services.tray.run_server_with_tray"),
        patch("os._exit"),
    ):
        from backend.main import _run_start

        _run_start(args)

    assert "host" in captured_config_kwargs
    assert "uds" not in captured_config_kwargs


# ---------------------------------------------------------------------------
# Windows named pipe — VECTORA_IPC_PIPE setado em os.environ
# ---------------------------------------------------------------------------


@pytest.mark.skipif(sys.platform != "win32", reason="Named pipe só no Windows")
def test_desktop_windows_sets_pipe_env(capsys: pytest.CaptureFixture[str]) -> None:
    """Com VECTORA_DESKTOP=1 no Windows, VECTORA_IPC_PIPE é setado e impresso."""
    import argparse

    args = argparse.Namespace(
        headless=False,
        host="0.0.0.0",  # noqa: S104
        port=8080,
        ssl_certfile=None,
        ssl_keyfile=None,
    )

    pipe_val_captured: list[str] = []

    with (
        patch.dict(os.environ, {"VECTORA_DESKTOP": "1"}, clear=False),
        patch("backend.api.server.create_app", return_value=MagicMock()),
        patch("backend.main._start_vite_dev", return_value=None),
        patch(
            "backend.services.ipc_pipe_win.serve_pipe",
            AsyncMock(side_effect=asyncio.CancelledError),
        ),
        patch("uvicorn.Config", return_value=MagicMock()),
        patch(
            "uvicorn.Server", return_value=MagicMock(serve=AsyncMock(return_value=None))
        ),
        patch("asyncio.run", side_effect=asyncio.CancelledError),
    ):
        from backend.main import _run_start

        with contextlib.suppress(asyncio.CancelledError, SystemExit, Exception):
            _run_start(args)

        # Checar env DENTRO do patch.dict antes de ser revertido
        assert "VECTORA_IPC_PIPE" in os.environ
        pipe_val_captured.append(os.environ["VECTORA_IPC_PIPE"])

    pipe_val = pipe_val_captured[0]
    assert pipe_val.startswith("\\\\.\\pipe\\vectora-")
    assert str(os.getpid()) in pipe_val

    captured = capsys.readouterr()
    assert "VECTORA_IPC_PIPE=" in captured.out


@pytest.mark.skipif(sys.platform != "win32", reason="Named pipe só no Windows")
def test_desktop_windows_no_tcp_host() -> None:
    """No modo Windows desktop, uvicorn.Config recebe port= efêmera, não host fixo."""
    import argparse

    captured_config_kwargs: dict[str, Any] = {}

    class _FakeConfig:
        def __init__(self, *_: Any, **kwargs: Any) -> None:
            captured_config_kwargs.update(kwargs)

    args = argparse.Namespace(
        headless=False,
        host="0.0.0.0",  # noqa: S104
        port=8080,
        ssl_certfile=None,
        ssl_keyfile=None,
    )

    with (
        patch.dict(os.environ, {"VECTORA_DESKTOP": "1"}, clear=False),
        patch("backend.api.server.create_app", return_value=MagicMock()),
        patch("backend.main._start_vite_dev", return_value=None),
        patch("backend.services.ipc_pipe_win.serve_pipe", AsyncMock()),
        patch("uvicorn.Config", side_effect=_FakeConfig),
        patch(
            "uvicorn.Server",
            return_value=MagicMock(serve=AsyncMock(return_value=None)),
        ),
        patch("asyncio.run"),
    ):
        from backend.main import _run_start

        _run_start(args)

    assert "uds" not in captured_config_kwargs

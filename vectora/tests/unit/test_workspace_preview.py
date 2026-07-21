"""Preview de workspace: health-check real de porta, não só "processo vivo".

Bug reproduzido ao vivo: `preview_status` considerava um dev server "rodando"
só porque o subprocesso existia (`proc.returncode is None`) — o iframe do
Workbench navegava pra lá antes do `vite`/`next` de fato bindar a porta,
resultando em `ERR_CONNECTION_REFUSED` repetido. Estes testes cobrem o novo
critério: a porta precisa aceitar conexão TCP de verdade.
"""

from __future__ import annotations

import asyncio
import socket

import pytest

from backend.api.handlers.workspaces import (
    _is_port_open,
    _wait_port_open,
    _wait_port_open_or_exit,
)


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.mark.asyncio
async def test_is_port_open_true_for_listening_socket():
    server = await asyncio.start_server(lambda r, w: None, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    try:
        assert await _is_port_open("127.0.0.1", port) is True
    finally:
        server.close()
        await server.wait_closed()


@pytest.mark.asyncio
async def test_is_port_open_false_for_closed_port():
    port = _free_port()
    assert await _is_port_open("127.0.0.1", port) is False


@pytest.mark.asyncio
async def test_wait_port_open_returns_true_once_server_starts():
    port = _free_port()
    server_holder: dict[str, asyncio.AbstractServer] = {}

    async def _start_server_after_delay():
        await asyncio.sleep(0.3)
        server_holder["server"] = await asyncio.start_server(
            lambda r, w: None, "127.0.0.1", port
        )

    starter = asyncio.ensure_future(_start_server_after_delay())
    try:
        ok = await _wait_port_open("127.0.0.1", port, total_timeout=3.0, interval=0.1)
        assert ok is True
    finally:
        await starter
        server = server_holder.get("server")
        if server is not None:
            server.close()
            await server.wait_closed()


@pytest.mark.asyncio
async def test_wait_port_open_times_out_when_nothing_listens():
    port = _free_port()
    ok = await _wait_port_open("127.0.0.1", port, total_timeout=0.5, interval=0.1)
    assert ok is False


# ---------------------------------------------------------------------------
# _wait_port_open_or_exit: encerra cedo se o processo morrer, sem esperar
# o timeout inteiro fazendo polling numa porta que nunca vai abrir.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_wait_port_open_or_exit_returns_open_true_when_port_opens():
    from unittest.mock import MagicMock

    port = _free_port()
    proc = MagicMock(returncode=None)
    server = await asyncio.start_server(lambda r, w: None, "127.0.0.1", port)
    try:
        opened, exit_code = await _wait_port_open_or_exit(
            proc, "127.0.0.1", port, total_timeout=3.0, interval=0.1
        )
        assert opened is True
        assert exit_code is None
    finally:
        server.close()
        await server.wait_closed()


@pytest.mark.asyncio
async def test_wait_port_open_or_exit_returns_early_when_process_dies():
    from unittest.mock import MagicMock

    port = _free_port()  # nada escutando aqui de propósito
    proc = MagicMock(returncode=1)  # já morto desde o início

    start = asyncio.get_event_loop().time()
    opened, exit_code = await _wait_port_open_or_exit(
        proc, "127.0.0.1", port, total_timeout=15.0, interval=0.1
    )
    elapsed = asyncio.get_event_loop().time() - start

    assert opened is False
    assert exit_code == 1
    # Erro/borda: não pode gastar o total_timeout inteiro (15s) só porque
    # o processo já tinha morrido — retorna quase na hora.
    assert elapsed < 1.0


# ---------------------------------------------------------------------------
# preview_status: running só quando processo vivo E porta aberta
# ---------------------------------------------------------------------------


class TestPreviewStatus:
    @pytest.mark.asyncio
    async def test_running_false_when_process_alive_but_port_closed(self, monkeypatch):
        from unittest.mock import AsyncMock, MagicMock

        import backend.api.handlers.workspaces as ws_mod

        cfg = MagicMock()
        cfg.configurations = [MagicMock(name="web", port=5173)]
        cfg.configurations[0].name = "web"
        proc = MagicMock(returncode=None, pid=123)

        monkeypatch.setattr(ws_mod, "get_launch_json", AsyncMock(return_value=cfg))
        monkeypatch.setattr(ws_mod, "_preview_procs", {"ws1::web": proc})
        monkeypatch.setattr(ws_mod, "_is_port_open", AsyncMock(return_value=False))

        result = await ws_mod.preview_status("ws1")

        assert result.servers[0].running is False

    @pytest.mark.asyncio
    async def test_running_true_when_process_alive_and_port_open(self, monkeypatch):
        from unittest.mock import AsyncMock, MagicMock

        import backend.api.handlers.workspaces as ws_mod

        cfg = MagicMock()
        cfg.configurations = [MagicMock(name="web", port=5173)]
        cfg.configurations[0].name = "web"
        proc = MagicMock(returncode=None, pid=123)

        monkeypatch.setattr(ws_mod, "get_launch_json", AsyncMock(return_value=cfg))
        monkeypatch.setattr(ws_mod, "_preview_procs", {"ws1::web": proc})
        monkeypatch.setattr(ws_mod, "_is_port_open", AsyncMock(return_value=True))

        result = await ws_mod.preview_status("ws1")

        assert result.servers[0].running is True
        assert result.servers[0].pid == 123


# ---------------------------------------------------------------------------
# preview_start: erro cedo quando o processo morre antes da porta abrir —
# bug reproduzido ao vivo: "Full Stack (Turbo)" (bun run dev) travava
# girando pra sempre com status="pending", sem nenhum log de erro.
# ---------------------------------------------------------------------------


class TestPreviewStart:
    @pytest.mark.asyncio
    async def test_returns_error_early_when_process_dies_before_port_opens(
        self, monkeypatch
    ):
        from unittest.mock import AsyncMock, MagicMock

        import backend.api.handlers.workspaces as ws_mod
        import backend.workspace.workspace as workspace_mod
        from backend.vtypes import Workspace

        ws = Workspace(
            id="ws1",
            name="ws1",
            cwd="/tmp/ws1",
            created_at="2024-01-01T00:00:00+00:00",
            trusted=True,
        )

        cfg_entry = MagicMock(
            port=59999, runtimeExecutable="false", runtimeArgs=[], env={}
        )
        cfg_entry.name = "web"
        launch_cfg = MagicMock()
        launch_cfg.configurations = [cfg_entry]

        proc = MagicMock()
        proc.returncode = 1  # já morto assim que spawnou
        proc.stdout = None

        monkeypatch.setattr(
            workspace_mod.workspace_registry,
            "get",
            lambda wid: ws if wid == "ws1" else None,
        )
        monkeypatch.setattr(
            ws_mod, "get_launch_json", AsyncMock(return_value=launch_cfg)
        )
        monkeypatch.setattr(ws_mod, "_preview_procs", {})
        monkeypatch.setattr(ws_mod, "_preview_log_tasks", {})
        monkeypatch.setattr(ws_mod, "_preview_log_buffers", {})
        monkeypatch.setattr(
            ws_mod._asyncio, "create_subprocess_exec", AsyncMock(return_value=proc)
        )

        result = await ws_mod.preview_start(
            "ws1", ws_mod.PreviewStartRequest(name="web")
        )

        assert result.status == "error"
        assert "1" in (result.message or "")


# ---------------------------------------------------------------------------
# preview_logs (endpoint) + buffer: log sobrevive ao processo morrer/parar,
# acessível tanto pela UI (este endpoint) quanto pelas tools do agente
# (mesmo dict `_preview_log_buffers`).
# ---------------------------------------------------------------------------


class TestPreviewLogsEndpoint:
    @pytest.mark.asyncio
    async def test_returns_empty_list_when_never_started(self, monkeypatch):
        import backend.api.handlers.workspaces as ws_mod

        monkeypatch.setattr(ws_mod, "_preview_log_buffers", {})

        result = await ws_mod.preview_logs("ws1", "web")

        assert result.lines == []

    @pytest.mark.asyncio
    async def test_returns_buffered_lines(self, monkeypatch):
        import collections

        import backend.api.handlers.workspaces as ws_mod

        buf: collections.deque[str] = collections.deque(["line1", "line2"], maxlen=500)
        monkeypatch.setattr(ws_mod, "_preview_log_buffers", {"ws1::web": buf})

        result = await ws_mod.preview_logs("ws1", "web")

        assert result.lines == ["line1", "line2"]

    @pytest.mark.asyncio
    async def test_buffer_survives_after_preview_stop(self, monkeypatch):
        # Erro/borda: parar o servidor não pode apagar o histórico — é
        # exatamente nesse momento (diagnosticar por que morreu) que ele
        # mais precisa continuar disponível.
        import collections
        from unittest.mock import AsyncMock, MagicMock

        import backend.api.handlers.workspaces as ws_mod

        buf: collections.deque[str] = collections.deque(["boom: error"], maxlen=500)
        proc = MagicMock(returncode=None)
        proc.terminate = MagicMock()
        proc.wait = AsyncMock(return_value=None)
        cfg_entry = MagicMock()
        cfg_entry.name = "web"
        launch_cfg = MagicMock()
        launch_cfg.configurations = [cfg_entry]

        monkeypatch.setattr(
            ws_mod, "get_launch_json", AsyncMock(return_value=launch_cfg)
        )
        monkeypatch.setattr(ws_mod, "_preview_procs", {"ws1::web": proc})
        monkeypatch.setattr(ws_mod, "_preview_log_tasks", {})
        monkeypatch.setattr(ws_mod, "_preview_log_buffers", {"ws1::web": buf})

        await ws_mod.preview_stop("ws1", ws_mod.PreviewStopRequest(name="web"))
        result = await ws_mod.preview_logs("ws1", "web")

        assert result.lines == ["boom: error"]


class TestPreviewStartPopulatesLogBuffer:
    @pytest.mark.asyncio
    async def test_lines_written_by_pipe_end_up_in_buffer(self, monkeypatch):
        from unittest.mock import AsyncMock, MagicMock

        import backend.api.handlers.workspaces as ws_mod
        import backend.workspace.workspace as workspace_mod
        from backend.vtypes import Workspace

        ws = Workspace(
            id="ws1",
            name="ws1",
            cwd="/tmp/ws1",
            created_at="2024-01-01T00:00:00+00:00",
            trusted=True,
        )
        cfg_entry = MagicMock(
            port=59998, runtimeExecutable="true", runtimeArgs=[], env={}
        )
        cfg_entry.name = "web"
        launch_cfg = MagicMock()
        launch_cfg.configurations = [cfg_entry]

        class _FakeStdout:
            def __init__(self, lines):
                self._lines = list(lines)

            async def readline(self):
                if not self._lines:
                    return b""
                return self._lines.pop(0)

        proc = MagicMock()
        proc.returncode = None
        proc.stdout = _FakeStdout([b"compiling...\n", b"ready\n", b""])

        monkeypatch.setattr(
            workspace_mod.workspace_registry,
            "get",
            lambda wid: ws if wid == "ws1" else None,
        )
        monkeypatch.setattr(
            ws_mod, "get_launch_json", AsyncMock(return_value=launch_cfg)
        )
        monkeypatch.setattr(ws_mod, "_preview_procs", {})
        monkeypatch.setattr(ws_mod, "_preview_log_tasks", {})
        monkeypatch.setattr(ws_mod, "_preview_log_buffers", {})
        monkeypatch.setattr(
            ws_mod._asyncio, "create_subprocess_exec", AsyncMock(return_value=proc)
        )
        monkeypatch.setattr(
            ws_mod, "_wait_port_open_or_exit", AsyncMock(return_value=(False, None))
        )

        await ws_mod.preview_start("ws1", ws_mod.PreviewStartRequest(name="web"))
        # Dá um tick pra task de background (pipe_to_logger) consumir o fake stdout.
        for _ in range(5):
            await asyncio.sleep(0)

        result = await ws_mod.preview_logs("ws1", "web")

        assert result.lines == ["compiling...", "ready"]

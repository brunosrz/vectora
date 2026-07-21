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

from backend.api.handlers.workspaces import _is_port_open, _wait_port_open


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

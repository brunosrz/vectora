"""NATS sidecar (D3) — spawn/readiness/shutdown do backend Python.

Mesmo padrão de sidecar que o Electron já usa pro backend Python
(resolve o binário, escolhe porta livre, lê stdout até o sinal de "pronto",
encerra limpo) — aqui é o próprio backend que sobe o nats-server, um nível
abaixo. Sem o binário disponível (dev sem instalação local, CI), degrada
pra None sem lançar — get_mq()/get_kv() caem pro fallback em memória.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.scheduling import nats_sidecar


@pytest.fixture(autouse=True)
def _reset_sidecar_state():
    nats_sidecar._proc = None
    nats_sidecar._url = None
    yield
    nats_sidecar._proc = None
    nats_sidecar._url = None


@pytest.mark.asyncio
async def test_ensure_nats_sidecar_returns_none_when_binary_not_found():
    with patch.object(nats_sidecar, "_resolve_binary", return_value=None):
        url = await nats_sidecar.ensure_nats_sidecar()

    assert url is None
    assert nats_sidecar._proc is None


def _fake_ready_proc(ready_line: bytes = b"Server is ready\n") -> MagicMock:
    proc = MagicMock()
    proc.stdout.readline = AsyncMock(return_value=ready_line)
    proc.returncode = None
    proc.kill = MagicMock()
    return proc


@pytest.mark.asyncio
async def test_ensure_nats_sidecar_spawns_and_returns_url_when_ready():
    fake_proc = _fake_ready_proc()

    with (
        patch.object(
            nats_sidecar, "_resolve_binary", return_value="/usr/bin/nats-server"
        ),
        patch(
            "asyncio.create_subprocess_exec",
            new=AsyncMock(return_value=fake_proc),
        ),
    ):
        url = await nats_sidecar.ensure_nats_sidecar()

    assert url is not None
    assert url.startswith("nats://127.0.0.1:")
    assert nats_sidecar._proc is fake_proc


@pytest.mark.asyncio
async def test_ensure_nats_sidecar_kills_process_and_returns_none_when_not_ready():
    """Edge — processo sobe mas nunca emite "Server is ready" (porta ocupada etc.)."""
    never_ready_proc = MagicMock()
    never_ready_proc.stdout.readline = AsyncMock(return_value=b"")  # EOF imediato
    never_ready_proc.kill = MagicMock()

    with (
        patch.object(
            nats_sidecar, "_resolve_binary", return_value="/usr/bin/nats-server"
        ),
        patch(
            "asyncio.create_subprocess_exec",
            new=AsyncMock(return_value=never_ready_proc),
        ),
    ):
        url = await nats_sidecar.ensure_nats_sidecar()

    assert url is None
    never_ready_proc.kill.assert_called_once()


@pytest.mark.asyncio
async def test_ensure_nats_sidecar_reuses_running_process():
    fake_proc = _fake_ready_proc()
    nats_sidecar._proc = fake_proc
    nats_sidecar._url = "nats://127.0.0.1:4222"

    with patch("asyncio.create_subprocess_exec", new=AsyncMock()) as spawn_mock:
        url = await nats_sidecar.ensure_nats_sidecar()

    assert url == "nats://127.0.0.1:4222"
    spawn_mock.assert_not_called()


@pytest.mark.asyncio
async def test_stop_nats_sidecar_terminates_and_clears_state():
    fake_proc = MagicMock()
    fake_proc.terminate = MagicMock()
    fake_proc.wait = AsyncMock(return_value=None)
    nats_sidecar._proc = fake_proc
    nats_sidecar._url = "nats://127.0.0.1:4222"

    await nats_sidecar.stop_nats_sidecar()

    fake_proc.terminate.assert_called_once()
    assert nats_sidecar._proc is None
    assert nats_sidecar.current_url() is None


@pytest.mark.asyncio
async def test_stop_nats_sidecar_without_running_process_is_noop():
    await nats_sidecar.stop_nats_sidecar()
    assert nats_sidecar._proc is None

"""Experiment — backend SSH do sandbox. Reaproveita SshTransport (mockado
nos testes, sem conexão real)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.sandbox.policy import SandboxPolicy
from backend.sandbox.ssh import run_ssh_sandboxed


@pytest.mark.asyncio
async def test_missing_remote_host_fails_closed_without_connecting():
    result = await run_ssh_sandboxed(
        ["ls"], "/ws", SandboxPolicy(enabled=True, backend="ssh")
    )

    assert result.exit_code == 126
    assert "remote_host" in result.stderr


@pytest.mark.asyncio
async def test_successful_run_returns_remote_output():
    fake_result = MagicMock(exit_code=0, stdout="hi\n", stderr="")
    fake_transport = MagicMock()
    fake_transport.run = AsyncMock(return_value=fake_result)
    fake_transport.close = AsyncMock()

    with patch("backend.transport.ssh.SshTransport", return_value=fake_transport):
        result = await run_ssh_sandboxed(
            ["echo", "hi"],
            "/ws",
            SandboxPolicy(enabled=True, backend="ssh", remote_host="user@host"),
        )

    assert result.exit_code == 0
    assert result.stdout == "hi\n"
    fake_transport.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_connection_failure_returns_clear_error_and_still_closes():
    fake_transport = MagicMock()
    fake_transport.run = AsyncMock(side_effect=RuntimeError("connection refused"))
    fake_transport.close = AsyncMock()

    with patch("backend.transport.ssh.SshTransport", return_value=fake_transport):
        result = await run_ssh_sandboxed(
            ["ls"],
            "/ws",
            SandboxPolicy(enabled=True, backend="ssh", remote_host="user@host"),
        )

    assert result.exit_code == 125
    assert "connection refused" in result.stderr
    fake_transport.close.assert_awaited_once()

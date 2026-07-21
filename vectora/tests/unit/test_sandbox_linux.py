"""AI Jail — linux.run_local_sandboxed: erro/borda de bwrap ausente e de
timeout, sem depender do binário real estar instalado."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.sandbox import linux as sandbox_linux
from backend.sandbox.policy import SandboxPolicy


@pytest.mark.asyncio
async def test_missing_bwrap_binary_returns_clear_error_not_exception(
    tmp_path, monkeypatch
):
    async def _raise_not_found(*_args, **_kwargs):
        raise FileNotFoundError("bwrap")

    monkeypatch.setattr(
        sandbox_linux.asyncio, "create_subprocess_exec", _raise_not_found
    )

    result = await sandbox_linux.run_local_sandboxed(
        ["ls"], str(tmp_path), SandboxPolicy(enabled=True)
    )

    assert result.exit_code == 127
    assert "bwrap" in result.stderr.lower()


@pytest.mark.asyncio
async def test_timeout_kills_process_and_reports_timed_out(tmp_path, monkeypatch):
    proc = MagicMock()

    async def _hang(*_args, **_kwargs):
        import asyncio

        await asyncio.sleep(10)

    proc.communicate = _hang
    proc.kill = MagicMock()
    proc.wait = AsyncMock()
    monkeypatch.setattr(
        sandbox_linux.asyncio, "create_subprocess_exec", AsyncMock(return_value=proc)
    )

    result = await sandbox_linux.run_local_sandboxed(
        ["sleep", "10"], str(tmp_path), SandboxPolicy(enabled=True), timeout_s=0.05
    )

    assert result.exit_code == 124
    assert result.timed_out is True
    proc.kill.assert_called_once()

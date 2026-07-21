"""Experiment — backend Modal do sandbox. SDK mockado via sys.modules (sem
custo real em CI, sem exigir credenciais)."""

from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock

import pytest

from backend.sandbox.policy import SandboxPolicy


@pytest.fixture(autouse=True)
def _no_real_modal_module(monkeypatch):
    # Garante que um `modal` real instalado no ambiente não interfira —
    # cada teste controla explicitamente se o import deve funcionar.
    monkeypatch.delitem(sys.modules, "modal", raising=False)


@pytest.mark.asyncio
async def test_missing_modal_sdk_degrades_with_clear_message(monkeypatch):
    monkeypatch.setitem(sys.modules, "modal", None)  # força ImportError

    from backend.sandbox.modal import run_modal_sandboxed

    result = await run_modal_sandboxed(["ls"], "/ws", SandboxPolicy(enabled=True))

    assert result.exit_code == 127
    assert "pip install modal" in result.stderr


@pytest.mark.asyncio
async def test_successful_run_returns_sandbox_output(monkeypatch):
    fake_process = MagicMock()
    fake_process.wait.return_value = 0
    fake_process.stdout.read.return_value = "hello\n"
    fake_process.stderr.read.return_value = ""

    fake_sandbox = MagicMock()
    fake_sandbox.exec.return_value = fake_process

    fake_app_cls = MagicMock()
    fake_app_cls.lookup.return_value = MagicMock()

    fake_modal = types.ModuleType("modal")
    fake_modal.App = fake_app_cls  # ty: ignore[unresolved-attribute]
    fake_modal.Sandbox = MagicMock()  # ty: ignore[unresolved-attribute]
    fake_modal.Sandbox.create.return_value = fake_sandbox
    monkeypatch.setitem(sys.modules, "modal", fake_modal)

    from backend.sandbox.modal import run_modal_sandboxed

    result = await run_modal_sandboxed(
        ["echo", "hello"], "/ws", SandboxPolicy(enabled=True)
    )

    assert result.exit_code == 0
    assert result.stdout == "hello\n"
    fake_sandbox.terminate.assert_called_once()


@pytest.mark.asyncio
async def test_sdk_failure_returns_clear_error_offering_other_backends(monkeypatch):
    fake_modal = types.ModuleType("modal")
    fake_modal.App = MagicMock()  # ty: ignore[unresolved-attribute]
    fake_modal.App.lookup.side_effect = RuntimeError("invalid token")
    fake_modal.Sandbox = MagicMock()  # ty: ignore[unresolved-attribute]
    monkeypatch.setitem(sys.modules, "modal", fake_modal)

    from backend.sandbox.modal import run_modal_sandboxed

    result = await run_modal_sandboxed(["ls"], "/ws", SandboxPolicy(enabled=True))

    assert result.exit_code == 125
    assert "outro backend" in result.stderr

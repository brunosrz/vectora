"""Experiment — backend Docker do sandbox. dry_run (build_docker_command)
testável sem o binário docker instalado; execução real mockada."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.sandbox.docker import build_docker_command, run_docker_sandboxed
from backend.sandbox.policy import SandboxPolicy


def test_build_docker_command_uses_default_image_and_mounts_workspace():
    argv = build_docker_command(SandboxPolicy(enabled=True), "/ws", ["ls"])

    assert argv[:3] == ["docker", "run", "--rm"]
    assert "-v" in argv
    v_idx = argv.index("-v")
    assert argv[v_idx + 1] == "/ws:/ws"
    assert argv[-2:] == ["python:3.13-slim", "ls"]


def test_build_docker_command_uses_configured_image():
    argv = build_docker_command(
        SandboxPolicy(enabled=True, docker_image="node:20-slim"), "/ws", ["true"]
    )

    assert "node:20-slim" in argv


def test_build_docker_command_lockdown_disables_network():
    argv = build_docker_command(
        SandboxPolicy(enabled=True, lockdown=True), "/ws", ["true"]
    )

    assert "--network" in argv
    assert argv[argv.index("--network") + 1] == "none"


@pytest.mark.asyncio
async def test_missing_docker_binary_returns_clear_error(tmp_path, monkeypatch):
    async def _raise_not_found(*_args, **_kwargs):
        raise FileNotFoundError("docker")

    monkeypatch.setattr(
        "backend.sandbox.docker.asyncio.create_subprocess_exec", _raise_not_found
    )

    result = await run_docker_sandboxed(
        ["ls"], str(tmp_path), SandboxPolicy(enabled=True)
    )

    assert result.exit_code == 127
    assert "docker" in result.stderr.lower()


@pytest.mark.asyncio
async def test_successful_run_returns_output(tmp_path, monkeypatch):
    proc = MagicMock()
    proc.communicate = AsyncMock(return_value=(b"hi\n", b""))
    proc.returncode = 0
    monkeypatch.setattr(
        "backend.sandbox.docker.asyncio.create_subprocess_exec",
        AsyncMock(return_value=proc),
    )

    result = await run_docker_sandboxed(
        ["echo", "hi"], str(tmp_path), SandboxPolicy(enabled=True)
    )

    assert result.exit_code == 0
    assert result.stdout == "hi\n"

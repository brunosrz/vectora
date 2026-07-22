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


@pytest.mark.asyncio
async def test_permission_denied_returns_clear_error_not_exception(
    tmp_path, monkeypatch
):
    async def _raise_permission_denied(*_args, **_kwargs):
        raise PermissionError("Permission denied: docker")

    monkeypatch.setattr(
        "backend.sandbox.docker.asyncio.create_subprocess_exec",
        _raise_permission_denied,
    )

    result = await run_docker_sandboxed(
        ["ls"], str(tmp_path), SandboxPolicy(enabled=True)
    )

    assert result.exit_code == 126
    assert "permissão" in result.stderr.lower()


@pytest.mark.asyncio
async def test_timeout_kills_container_process_and_reports_timed_out(
    tmp_path, monkeypatch
):
    proc = MagicMock()

    async def _hang(*_args, **_kwargs):
        import asyncio

        await asyncio.sleep(10)

    proc.communicate = _hang
    proc.kill = MagicMock()
    proc.wait = AsyncMock()
    monkeypatch.setattr(
        "backend.sandbox.docker.asyncio.create_subprocess_exec",
        AsyncMock(return_value=proc),
    )

    result = await run_docker_sandboxed(
        ["sleep", "10"], str(tmp_path), SandboxPolicy(enabled=True), timeout_s=0.05
    )

    assert result.exit_code == 124
    assert result.timed_out is True
    proc.kill.assert_called_once()


@pytest.mark.asyncio
async def test_nonzero_exit_code_from_container_is_propagated(tmp_path, monkeypatch):
    proc = MagicMock()
    proc.communicate = AsyncMock(return_value=(b"", b"comando falhou\n"))
    proc.returncode = 1
    monkeypatch.setattr(
        "backend.sandbox.docker.asyncio.create_subprocess_exec",
        AsyncMock(return_value=proc),
    )

    result = await run_docker_sandboxed(
        ["false"], str(tmp_path), SandboxPolicy(enabled=True)
    )

    assert result.exit_code == 1
    assert result.stderr == "comando falhou\n"


def test_build_docker_command_with_empty_command_list_still_ends_with_image():
    argv = build_docker_command(SandboxPolicy(enabled=True), "/ws", [])

    assert argv[-1] == "python:3.13-slim"


def test_build_docker_command_lockdown_false_omits_network_flag():
    argv = build_docker_command(
        SandboxPolicy(enabled=True, lockdown=False), "/ws", ["true"]
    )

    assert "--network" not in argv


def test_build_docker_command_workspace_with_spaces_and_unicode():
    argv = build_docker_command(
        SandboxPolicy(enabled=True), "/home/usuário/meu projeto", ["ls"]
    )

    v_idx = argv.index("-v")
    assert argv[v_idx + 1] == "/home/usuário/meu projeto:/home/usuário/meu projeto"

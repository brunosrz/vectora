"""AI Jail — runner.run_sandboxed: dispatcher que lê vectora.toml e decide
se roda dentro do sandbox ou sem wrapper (comportamento atual preservado
quando não há política configurada).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.sandbox import runner


def _fake_proc(stdout=b"ok\n", stderr=b"", returncode=0):
    proc = MagicMock()
    proc.communicate = AsyncMock(return_value=(stdout, stderr))
    proc.returncode = returncode
    proc.kill = MagicMock()
    proc.wait = AsyncMock()
    return proc


@pytest.mark.asyncio
async def test_no_vectora_toml_runs_unsandboxed(tmp_path, monkeypatch):
    proc = _fake_proc(stdout=b"hello\n")
    create_mock = AsyncMock(return_value=proc)
    monkeypatch.setattr(runner.asyncio, "create_subprocess_exec", create_mock)

    result = await runner.run_sandboxed(["echo", "hello"], str(tmp_path))

    assert result.exit_code == 0
    assert result.stdout == "hello\n"
    # Sem policy, comando roda direto — nunca prefixado com "bwrap".
    called_args = create_mock.call_args.args
    assert called_args[0] == "echo"


@pytest.mark.asyncio
async def test_enabled_local_policy_dispatches_to_bwrap(tmp_path, monkeypatch):
    (tmp_path / "vectora.toml").write_text(
        '[sandbox]\nenabled = true\nbackend = "local"\n', encoding="utf-8"
    )
    proc = _fake_proc(stdout=b"sandboxed\n")
    create_mock = AsyncMock(return_value=proc)
    monkeypatch.setattr(runner.asyncio, "create_subprocess_exec", create_mock)

    result = await runner.run_sandboxed(["ls"], str(tmp_path))

    assert result.exit_code == 0
    assert result.stdout == "sandboxed\n"
    called_args = create_mock.call_args.args
    assert called_args[0] == "bwrap"


@pytest.mark.asyncio
async def test_unknown_backend_fails_closed_without_running_anything(
    tmp_path, monkeypatch
):
    (tmp_path / "vectora.toml").write_text(
        '[sandbox]\nenabled = true\nbackend = "singularity"\n', encoding="utf-8"
    )
    create_mock = AsyncMock()
    monkeypatch.setattr(runner.asyncio, "create_subprocess_exec", create_mock)

    result = await runner.run_sandboxed(["ls"], str(tmp_path))

    assert result.exit_code == 126
    assert "singularity" in result.stderr
    create_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_docker_backend_dispatches_to_docker_run(tmp_path, monkeypatch):
    (tmp_path / "vectora.toml").write_text(
        '[sandbox]\nenabled = true\nbackend = "docker"\n', encoding="utf-8"
    )
    proc = _fake_proc(stdout=b"in-container\n")
    create_mock = AsyncMock(return_value=proc)
    monkeypatch.setattr(runner.asyncio, "create_subprocess_exec", create_mock)

    result = await runner.run_sandboxed(["ls"], str(tmp_path))

    assert result.exit_code == 0
    assert result.stdout == "in-container\n"
    called_args = create_mock.call_args.args
    assert called_args[0] == "docker"


@pytest.mark.asyncio
async def test_ssh_backend_without_remote_host_fails_closed(tmp_path):
    (tmp_path / "vectora.toml").write_text(
        '[sandbox]\nenabled = true\nbackend = "ssh"\n', encoding="utf-8"
    )

    result = await runner.run_sandboxed(["ls"], str(tmp_path))

    assert result.exit_code == 126
    assert "remote_host" in result.stderr


@pytest.mark.asyncio
async def test_disabled_sandbox_section_runs_unsandboxed(tmp_path, monkeypatch):
    (tmp_path / "vectora.toml").write_text(
        "[sandbox]\nenabled = false\n", encoding="utf-8"
    )
    proc = _fake_proc()
    create_mock = AsyncMock(return_value=proc)
    monkeypatch.setattr(runner.asyncio, "create_subprocess_exec", create_mock)

    result = await runner.run_sandboxed(["true"], str(tmp_path))

    assert result.exit_code == 0
    called_args = create_mock.call_args.args
    assert called_args[0] == "true"

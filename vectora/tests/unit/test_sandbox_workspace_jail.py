"""AI Jail — WorkspaceJailManager/JailedWorker: worker persistente por
workspace (não um bwrap novo a cada tool call)."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.sandbox import workspace_jail as wj
from backend.sandbox.policy import SandboxPolicy


def _fake_proc(returncode: int | None = None) -> MagicMock:
    proc = MagicMock()
    proc.returncode = returncode
    proc.stdin = MagicMock()
    proc.stdin.write = MagicMock()
    proc.stdin.drain = AsyncMock()
    proc.stdout = MagicMock()
    proc.terminate = MagicMock()
    proc.kill = MagicMock()
    proc.wait = AsyncMock()
    return proc


@pytest.mark.asyncio
async def test_disabled_policy_raises_without_spawning(tmp_path, monkeypatch):
    spawn_mock = AsyncMock()
    monkeypatch.setattr(wj.asyncio, "create_subprocess_exec", spawn_mock)
    manager = wj.WorkspaceJailManager()

    with pytest.raises(wj.WorkerSpawnError):
        await manager.get_or_spawn("ws-1", str(tmp_path), SandboxPolicy(enabled=False))

    spawn_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_reuses_same_worker_for_same_workspace(tmp_path, monkeypatch):
    proc = _fake_proc()
    spawn_mock = AsyncMock(return_value=proc)
    monkeypatch.setattr(wj.asyncio, "create_subprocess_exec", spawn_mock)
    manager = wj.WorkspaceJailManager()
    policy = SandboxPolicy(enabled=True)

    w1 = await manager.get_or_spawn("ws-1", str(tmp_path), policy)
    w2 = await manager.get_or_spawn("ws-1", str(tmp_path), policy)

    assert w1 is w2
    spawn_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_missing_bwrap_raises_clear_error(tmp_path, monkeypatch):
    async def _raise_not_found(*_args, **_kwargs):
        raise FileNotFoundError("bwrap")

    monkeypatch.setattr(wj.asyncio, "create_subprocess_exec", _raise_not_found)
    manager = wj.WorkspaceJailManager()

    with pytest.raises(wj.WorkerSpawnError, match="bwrap"):
        await manager.get_or_spawn("ws-1", str(tmp_path), SandboxPolicy(enabled=True))


@pytest.mark.asyncio
async def test_request_writes_json_line_and_parses_response(tmp_path, monkeypatch):
    proc = _fake_proc()
    response = json.dumps({"id": 1, "stdout": "ok\n", "stderr": "", "exit_code": 0})
    proc.stdout.readline = AsyncMock(return_value=(response + "\n").encode("utf-8"))
    spawn_mock = AsyncMock(return_value=proc)
    monkeypatch.setattr(wj.asyncio, "create_subprocess_exec", spawn_mock)
    manager = wj.WorkspaceJailManager()

    worker = await manager.get_or_spawn(
        "ws-1", str(tmp_path), SandboxPolicy(enabled=True)
    )
    result = await worker.request("exec", command=["echo", "ok"])

    assert result == {"id": 1, "stdout": "ok\n", "stderr": "", "exit_code": 0}
    sent = json.loads(proc.stdin.write.call_args[0][0].decode("utf-8"))
    assert sent == {"op": "exec", "id": 1, "command": ["echo", "ok"]}


@pytest.mark.asyncio
async def test_request_raises_when_worker_closes_stdout(tmp_path, monkeypatch):
    proc = _fake_proc()
    proc.stdout.readline = AsyncMock(return_value=b"")
    monkeypatch.setattr(
        wj.asyncio, "create_subprocess_exec", AsyncMock(return_value=proc)
    )
    manager = wj.WorkspaceJailManager()
    worker = await manager.get_or_spawn(
        "ws-1", str(tmp_path), SandboxPolicy(enabled=True)
    )

    with pytest.raises(RuntimeError, match="encerrou"):
        await worker.request("exec", command=["echo"])


@pytest.mark.asyncio
async def test_close_idle_terminates_stale_workers_and_respawns(tmp_path, monkeypatch):
    proc = _fake_proc()
    spawn_mock = AsyncMock(return_value=proc)
    monkeypatch.setattr(wj.asyncio, "create_subprocess_exec", spawn_mock)
    manager = wj.WorkspaceJailManager(idle_timeout_s=0.0)
    policy = SandboxPolicy(enabled=True)

    worker = await manager.get_or_spawn("ws-1", str(tmp_path), policy)
    worker.last_used -= 1.0  # força "ocioso"

    await manager.close_idle()
    proc.terminate.assert_called_once()

    await manager.get_or_spawn("ws-1", str(tmp_path), policy)
    assert spawn_mock.await_count == 2


@pytest.mark.asyncio
async def test_close_idle_keeps_recently_used_workers(tmp_path, monkeypatch):
    proc = _fake_proc()
    spawn_mock = AsyncMock(return_value=proc)
    monkeypatch.setattr(wj.asyncio, "create_subprocess_exec", spawn_mock)
    manager = wj.WorkspaceJailManager(idle_timeout_s=600.0)
    policy = SandboxPolicy(enabled=True)

    await manager.get_or_spawn("ws-1", str(tmp_path), policy)
    await manager.close_idle()

    proc.terminate.assert_not_called()
    await manager.get_or_spawn("ws-1", str(tmp_path), policy)
    spawn_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_is_alive_reflects_returncode(tmp_path, monkeypatch):
    dead_proc = _fake_proc(returncode=1)
    spawn_mock = AsyncMock(return_value=dead_proc)
    monkeypatch.setattr(wj.asyncio, "create_subprocess_exec", spawn_mock)
    manager = wj.WorkspaceJailManager()
    policy = SandboxPolicy(enabled=True)

    await manager.get_or_spawn("ws-1", str(tmp_path), policy)
    # worker morto (returncode != None) — próxima chamada nasce um novo
    await manager.get_or_spawn("ws-1", str(tmp_path), policy)

    assert spawn_mock.await_count == 2

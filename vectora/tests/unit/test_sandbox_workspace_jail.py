"""AI Jail — WorkspaceJailManager/JailedWorker: worker persistente por
workspace (não um bwrap novo a cada tool call)."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.sandbox import workspace_jail as wj
from backend.sandbox.policy import SandboxPolicy


@pytest.fixture(autouse=True)
def _force_linux_platform(monkeypatch):
    # Testes abaixo exercitam o caminho bwrap nativo (Linux) — forçar a
    # plataforma torna isso determinístico independente do SO onde os
    # testes rodam de verdade (esta máquina de dev é Windows). Monkeypatcha
    # `_is_windows` (indireção local), não `sys.platform` direto — mexer no
    # `sys` global quebra pytest-asyncio/outras libs que também leem
    # `sys.platform` no mesmo processo. O caminho WSL2 (win32) tem sua
    # própria seção de testes abaixo.
    monkeypatch.setattr(wj, "_is_windows", lambda: False)


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
async def test_spawn_aplica_seccomp_fd_quando_filtro_disponivel(tmp_path, monkeypatch):
    proc = _fake_proc()
    spawn_mock = AsyncMock(return_value=proc)
    monkeypatch.setattr(wj.asyncio, "create_subprocess_exec", spawn_mock)
    monkeypatch.setattr(wj, "build_seccomp_filter", lambda: b"BPF-PROGRAM")
    manager = wj.WorkspaceJailManager()

    await manager.get_or_spawn("ws-1", str(tmp_path), SandboxPolicy(enabled=True))

    assert spawn_mock.await_args is not None
    argv = spawn_mock.await_args.args
    assert argv[0] == "bwrap"
    assert "--seccomp" in argv
    kwargs = spawn_mock.await_args.kwargs
    assert kwargs["pass_fds"] != ()


@pytest.mark.asyncio
async def test_spawn_degrada_sem_seccomp_quando_libseccomp_ausente(
    tmp_path, monkeypatch
):
    proc = _fake_proc()
    spawn_mock = AsyncMock(return_value=proc)
    monkeypatch.setattr(wj.asyncio, "create_subprocess_exec", spawn_mock)
    monkeypatch.setattr(wj, "build_seccomp_filter", lambda: None)
    manager = wj.WorkspaceJailManager()

    await manager.get_or_spawn("ws-1", str(tmp_path), SandboxPolicy(enabled=True))

    assert spawn_mock.await_args is not None
    argv = spawn_mock.await_args.args
    assert "--seccomp" not in argv
    kwargs = spawn_mock.await_args.kwargs
    assert kwargs["pass_fds"] == ()


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


def test_windows_path_to_wsl_traduz_drive_e_barras():
    assert wj._windows_path_to_wsl(r"C:\Users\dev\meu projeto") == (
        "/mnt/c/Users/dev/meu projeto"
    )


def test_windows_path_to_wsl_raiz_do_drive_sem_barra_sobrando():
    assert wj._windows_path_to_wsl("D:\\") == "/mnt/d"


class TestWsl2Spawn:
    """No Windows (`sys.platform == "win32"`), bwrap não roda nativo — o
    worker é roteado inteiro por dentro de uma distro WSL2 via `wsl.exe`."""

    @pytest.fixture(autouse=True)
    def _win32(self, monkeypatch):
        monkeypatch.setattr(wj, "_is_windows", lambda: True)

    @pytest.mark.asyncio
    async def test_roteia_via_wsl_exe_e_traduz_o_workspace_dir(self, monkeypatch):
        proc = _fake_proc()
        spawn_mock = AsyncMock(return_value=proc)
        monkeypatch.setattr(wj.asyncio, "create_subprocess_exec", spawn_mock)
        monkeypatch.setattr(wj, "detect_wsl2", AsyncMock(return_value="Ubuntu"))
        monkeypatch.setattr(
            wj, "_bwrap_available_in_distro", AsyncMock(return_value=True)
        )
        manager = wj.WorkspaceJailManager()

        await manager.get_or_spawn(
            "ws-1", r"C:\Users\dev\projeto", SandboxPolicy(enabled=True)
        )

        assert spawn_mock.await_args is not None
        argv = spawn_mock.await_args.args
        assert argv[0] == "wsl.exe"
        assert argv[1:4] == ("-d", "Ubuntu", "--")
        assert "bwrap" in argv
        assert "/mnt/c/Users/dev/projeto" in argv
        assert "python3" in argv
        # sys.executable (path do Windows) nunca deve vazar pro argv do WSL.
        assert wj.sys.executable not in argv

    @pytest.mark.asyncio
    async def test_sem_wsl2_disponivel_falha_com_mensagem_acionavel(self, monkeypatch):
        spawn_mock = AsyncMock()
        monkeypatch.setattr(wj.asyncio, "create_subprocess_exec", spawn_mock)
        monkeypatch.setattr(wj, "detect_wsl2", AsyncMock(return_value=None))
        manager = wj.WorkspaceJailManager()

        with pytest.raises(wj.WorkerSpawnError, match="WSL2"):
            await manager.get_or_spawn(
                "ws-1", r"C:\Users\dev\projeto", SandboxPolicy(enabled=True)
            )
        spawn_mock.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_wsl2_disponivel_mas_sem_bwrap_dentro_da_distro_falha_com_mensagem_acionavel(
        self, monkeypatch
    ):
        spawn_mock = AsyncMock()
        monkeypatch.setattr(wj.asyncio, "create_subprocess_exec", spawn_mock)
        monkeypatch.setattr(wj, "detect_wsl2", AsyncMock(return_value="Ubuntu"))
        monkeypatch.setattr(
            wj, "_bwrap_available_in_distro", AsyncMock(return_value=False)
        )
        manager = wj.WorkspaceJailManager()

        with pytest.raises(wj.WorkerSpawnError, match="bubblewrap"):
            await manager.get_or_spawn(
                "ws-1", r"C:\Users\dev\projeto", SandboxPolicy(enabled=True)
            )
        spawn_mock.assert_not_awaited()

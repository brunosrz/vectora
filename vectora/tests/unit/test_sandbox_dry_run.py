"""AI Jail — dry_run: monta o argv do `bwrap` sem precisar do binário real
instalado (CI-friendly)."""

from __future__ import annotations

from backend.sandbox.dry_run import build_bwrap_command
from backend.sandbox.policy import SandboxPolicy


def test_command_contains_workspace_bind_and_trailing_command():
    policy = SandboxPolicy(enabled=True)

    argv = build_bwrap_command(policy, "/home/user/project", ["ls", "-la"])

    assert argv[0] == "bwrap"
    assert "--bind" in argv
    idx = argv.index("--bind")
    assert argv[idx + 1 : idx + 3] == ["/home/user/project", "/home/user/project"]
    assert argv[-3:] == ["--", "ls", "-la"]


def test_rw_and_ro_paths_are_mounted():
    policy = SandboxPolicy(enabled=True, rw_paths=("/data",), ro_paths=("/opt/tools",))

    argv = build_bwrap_command(policy, "/ws", ["true"])

    data_idx = argv.index("/data")
    assert argv[data_idx - 1 : data_idx + 2] == ["--bind", "/data", "/data"]
    tools_idx = argv.index("/opt/tools")
    assert argv[tools_idx - 1 : tools_idx + 2] == [
        "--ro-bind",
        "/opt/tools",
        "/opt/tools",
    ]


def test_mask_paths_become_tmpfs():
    policy = SandboxPolicy(enabled=True, mask=(".env", "**/*.pem"))

    argv = build_bwrap_command(policy, "/ws", ["true"])

    assert argv.count("--tmpfs") == 2
    tmpfs_idx = argv.index("--tmpfs")
    assert argv[tmpfs_idx + 1] == ".env"


def test_lockdown_adds_unshare_net():
    locked = build_bwrap_command(
        SandboxPolicy(enabled=True, lockdown=True), "/ws", ["true"]
    )
    unlocked = build_bwrap_command(
        SandboxPolicy(enabled=True, lockdown=False), "/ws", ["true"]
    )

    assert "--unshare-net" in locked
    assert "--unshare-net" not in unlocked


def test_no_mounts_when_policy_has_none_configured():
    # Erro/borda: rw_paths/ro_paths/mask todos vazios não deve quebrar a
    # montagem — só o essencial (workspace + sistema) fica no comando.
    policy = SandboxPolicy(enabled=True, rw_paths=(), ro_paths=(), mask=())

    argv = build_bwrap_command(policy, "/ws", ["true"])

    assert argv.count("--tmpfs") == 0
    # Apenas o bind do próprio workspace deve existir (nenhum --bind extra).
    assert argv.count("--bind") == 1

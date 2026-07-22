"""AI Jail — dry_run: monta o argv do `bwrap` sem precisar do binário real
instalado (CI-friendly)."""

from __future__ import annotations

import pytest

from backend.sandbox.dry_run import DENIED_SYSCALLS, build_bwrap_command
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


def test_empty_command_still_produces_valid_argv_with_trailing_separator():
    # Erro/borda: comando vazio não deve quebrar a montagem — o "--" fica
    # sozinho no final, sem nenhum argumento de comando depois dele.
    argv = build_bwrap_command(SandboxPolicy(enabled=True), "/ws", [])

    assert argv[-1] == "--"


def test_multiple_rw_and_ro_paths_preserve_order():
    policy = SandboxPolicy(
        enabled=True,
        rw_paths=("/a", "/b", "/c"),
        ro_paths=("/x", "/y"),
    )

    argv = build_bwrap_command(policy, "/ws", ["true"])

    rw_binds = [argv[i + 1] for i, tok in enumerate(argv) if tok == "--bind"]
    assert rw_binds == ["/ws", "/a", "/b", "/c"]
    ro_binds = [argv[i + 1] for i, tok in enumerate(argv) if tok == "--ro-bind"]
    # os três primeiros --ro-bind são /usr /bin /lib fixos do sistema.
    assert ro_binds[-2:] == ["/x", "/y"]


def test_paths_with_spaces_and_unicode_pass_through_unchanged():
    policy = SandboxPolicy(enabled=True, rw_paths=("/home/usuário/meu projeto",))

    argv = build_bwrap_command(policy, "/ws", ["true"])

    assert "/home/usuário/meu projeto" in argv


def test_command_arguments_with_spaces_and_quotes_pass_through_unchanged():
    argv = build_bwrap_command(
        SandboxPolicy(enabled=True), "/ws", ["echo", "hello world", '"quoted"']
    )

    assert argv[-3:] == ["echo", "hello world", '"quoted"']


def test_docker_and_ssh_only_fields_are_ignored_by_bwrap_command():
    # docker_image/remote_host/ssh_key_id não fazem sentido pro backend
    # local — não devem vazar pro argv do bwrap.
    policy = SandboxPolicy(
        enabled=True,
        docker_image="node:20-slim",
        remote_host="user@host",
        ssh_key_id="key-1",
    )

    argv = build_bwrap_command(policy, "/ws", ["true"])

    assert "node:20-slim" not in argv
    assert "user@host" not in argv
    assert "key-1" not in argv


def test_denied_syscalls_list_contains_expected_dangerous_calls():
    for name in ("ptrace", "bpf", "mount", "unshare", "reboot"):
        assert name in DENIED_SYSCALLS


def test_denied_syscalls_is_immutable_tuple():
    assert isinstance(DENIED_SYSCALLS, tuple)
    with pytest.raises(TypeError):
        DENIED_SYSCALLS[0] = "ptrace"  # ty: ignore[invalid-assignment]


def test_workspace_dir_appears_exactly_once_as_bind_source():
    argv = build_bwrap_command(SandboxPolicy(enabled=True), "/ws/project", ["true"])

    bind_idx = argv.index("--bind")
    assert argv[bind_idx + 1] == "/ws/project"
    assert argv[bind_idx + 2] == "/ws/project"
    assert "--chdir" in argv
    chdir_idx = argv.index("--chdir")
    assert argv[chdir_idx + 1] == "/ws/project"

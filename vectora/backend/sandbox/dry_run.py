"""Serializa o comando `bwrap` a partir de uma `SandboxPolicy`, sem executar.

Usado tanto por uma futura flag de auditoria quanto pelos testes — permite
validar a lógica de montagem de mounts/flags sem precisar do binário
`bwrap` instalado (CI-friendly).
"""

from __future__ import annotations

from backend.sandbox.policy import SandboxPolicy

# Denylist de syscalls perigosas (ptrace/module loading/bpf/namespace
# escape) — mesmo espírito do ai-jail original. Aplicada via seccomp-bpf
# real em `linux.py`; aqui só documentamos/expomos a lista pros testes.
DENIED_SYSCALLS: tuple[str, ...] = (
    "ptrace",
    "process_vm_readv",
    "process_vm_writev",
    "bpf",
    "init_module",
    "finit_module",
    "delete_module",
    "kexec_load",
    "mount",
    "umount2",
    "pivot_root",
    "unshare",
    "personality",
    "reboot",
)


def build_bwrap_command(
    policy: SandboxPolicy, workspace_dir: str, command: list[str]
) -> list[str]:
    """Monta o argv completo de `bwrap` — namespaces PID/UTS/IPC isolados,
    workspace em rw, sistema em ro, `rw_paths`/`ro_paths` da política
    montados conforme declarado, `mask` como tmpfs vazio (oculta o
    conteúdo real sem impedir o path de existir), `lockdown` também nega
    rede (`--unshare-net`)."""
    argv: list[str] = [
        "bwrap",
        "--unshare-pid",
        "--unshare-uts",
        "--unshare-ipc",
        "--die-with-parent",
        "--proc",
        "/proc",
        "--dev",
        "/dev",
        "--ro-bind",
        "/usr",
        "/usr",
        "--ro-bind",
        "/bin",
        "/bin",
        "--ro-bind",
        "/lib",
        "/lib",
    ]
    argv += ["--bind", workspace_dir, workspace_dir]
    for path in policy.rw_paths:
        argv += ["--bind", path, path]
    for path in policy.ro_paths:
        argv += ["--ro-bind", path, path]
    for masked in policy.mask:
        argv += ["--tmpfs", masked]
    if policy.lockdown:
        argv += ["--unshare-net"]
    argv += ["--chdir", workspace_dir]
    argv += ["--", *command]
    return argv

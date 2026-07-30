"""Landlock LSM (Linux 5.13+) — restrição de filesystem complementar aos
binds do `bwrap`, defesa em profundidade (nega acesso mesmo se um bind
do bwrap "vazasse" por engano). As 3 syscalls
(`landlock_create_ruleset`/`landlock_add_rule`/`landlock_restrict_self`)
não têm wrapper no glibc (man7.org/landlock_create_ruleset(2)) —
chamadas aqui via `ctypes` cru (`syscall()`), sem dependência nova.
Degradação graciosa sempre: kernel <5.13, arquitetura não mapeada, ou
qualquer falha de syscall vira log de aviso e `False` — nunca exceção,
mesmo padrão de `linux.py::build_seccomp_filter`.
"""

from __future__ import annotations

import ctypes
import logging
import os
import platform

logger = logging.getLogger(__name__)

# __NR_landlock_* — os 3 números são os mesmos no x86_64 e na tabela
# genérica de syscall usada por arm64 (fixados desde o merge original em
# 5.13, "arch: Wire up Landlock syscalls"). Arquiteturas fora deste mapa
# degradam sem tentar a syscall (evita chamar um número errado).
_SYSCALL_NUMBERS: dict[str, tuple[int, int, int]] = {
    "x86_64": (444, 445, 446),
    "aarch64": (444, 445, 446),
}

_PR_SET_NO_NEW_PRIVS = 38
_LANDLOCK_RULE_PATH_BENEATH = 1

# ABI V1 (5.13+) — todos os direitos de filesystem definidos na v1 do
# uapi/linux/landlock.h. V2 (renomear/linkar) e V3 (truncar) exigem
# 5.19+/6.2+ — fora de escopo desta sprint (defesa V1 já cobre o caso de
# uso: negar leitura/escrita fora dos paths declarados na política).
_ACCESS_FS_EXECUTE = 1 << 0
_ACCESS_FS_WRITE_FILE = 1 << 1
_ACCESS_FS_READ_FILE = 1 << 2
_ACCESS_FS_READ_DIR = 1 << 3
_ACCESS_FS_REMOVE_DIR = 1 << 4
_ACCESS_FS_REMOVE_FILE = 1 << 5
_ACCESS_FS_MAKE_CHAR = 1 << 6
_ACCESS_FS_MAKE_DIR = 1 << 7
_ACCESS_FS_MAKE_REG = 1 << 8
_ACCESS_FS_MAKE_SOCK = 1 << 9
_ACCESS_FS_MAKE_FIFO = 1 << 10
_ACCESS_FS_MAKE_BLOCK = 1 << 11
_ACCESS_FS_MAKE_SYM = 1 << 12

ACCESS_FS_V1_ALL = (
    _ACCESS_FS_EXECUTE
    | _ACCESS_FS_WRITE_FILE
    | _ACCESS_FS_READ_FILE
    | _ACCESS_FS_READ_DIR
    | _ACCESS_FS_REMOVE_DIR
    | _ACCESS_FS_REMOVE_FILE
    | _ACCESS_FS_MAKE_CHAR
    | _ACCESS_FS_MAKE_DIR
    | _ACCESS_FS_MAKE_REG
    | _ACCESS_FS_MAKE_SOCK
    | _ACCESS_FS_MAKE_FIFO
    | _ACCESS_FS_MAKE_BLOCK
    | _ACCESS_FS_MAKE_SYM
)
ACCESS_FS_READ_ONLY = _ACCESS_FS_EXECUTE | _ACCESS_FS_READ_FILE | _ACCESS_FS_READ_DIR


class _RulesetAttr(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("handled_access_fs", ctypes.c_uint64),
        ("handled_access_net", ctypes.c_uint64),
    ]


class _PathBeneathAttr(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("allowed_access", ctypes.c_uint64),
        ("parent_fd", ctypes.c_int32),
    ]


def _syscall_numbers() -> tuple[int, int, int] | None:
    return _SYSCALL_NUMBERS.get(platform.machine())


def _add_path_rule(
    libc: ctypes.CDLL, add_rule_nr: int, ruleset_fd: int, path: str, access: int
) -> bool:
    """Concede `access` sobre `path` no ruleset. Path inexistente não é
    erro fatal (mesmo espírito do mask sem match, Sprint 4.4) — o worker
    simplesmente nunca teve acesso a ele de qualquer forma."""
    try:
        parent_fd = os.open(
            path,
            os.O_PATH | os.O_CLOEXEC,
        )
    except OSError:
        logger.debug("sandbox: path %r inexistente pro Landlock — ignorando", path)
        return True

    try:
        rule = _PathBeneathAttr(allowed_access=access, parent_fd=parent_fd)
        rc = libc.syscall(
            add_rule_nr,
            ruleset_fd,
            _LANDLOCK_RULE_PATH_BENEATH,
            ctypes.byref(rule),
            0,
        )
        if rc != 0:
            logger.warning(
                "sandbox: landlock_add_rule falhou pro path %r (errno=%s)",
                path,
                ctypes.get_errno(),
            )
            return False
        return True
    finally:
        os.close(parent_fd)


def apply_landlock(rw_paths: list[str], ro_paths: list[str]) -> bool:
    """Restringe o processo atual (e todo filho `exec`ado depois) a
    `rw_paths` (leitura+escrita+criação) e `ro_paths` (só leitura/
    travessia) via Landlock V1 — chamado uma única vez, no worker
    jailado, logo após `apply_rlimits`. Devolve `True` se aplicado com
    sucesso; `False` em qualquer degradação (kernel <5.13, arquitetura
    não suportada, syscall indisponível/negada) — nunca levanta, o
    worker sempre segue rodando (namespaces do bwrap continuam valendo
    de qualquer forma)."""
    numbers = _syscall_numbers()
    if numbers is None:
        logger.info(
            "sandbox: Landlock não mapeado pra esta arquitetura (%s) — "
            "seguindo sem (namespaces do bwrap continuam ativos)",
            platform.machine(),
        )
        return False

    create_nr, add_rule_nr, restrict_self_nr = numbers
    libc = ctypes.CDLL(None, use_errno=True)

    attr = _RulesetAttr(handled_access_fs=ACCESS_FS_V1_ALL, handled_access_net=0)
    ruleset_fd = libc.syscall(create_nr, ctypes.byref(attr), ctypes.sizeof(attr), 0)
    if ruleset_fd < 0:
        logger.warning(
            "sandbox: landlock_create_ruleset falhou (errno=%s) — kernel sem "
            "suporte a Landlock (precisa 5.13+) ou syscall bloqueada — "
            "seguindo sem Landlock",
            ctypes.get_errno(),
        )
        return False

    try:
        rules_ok = True
        for path in rw_paths:
            rules_ok = (
                _add_path_rule(libc, add_rule_nr, ruleset_fd, path, ACCESS_FS_V1_ALL)
                and rules_ok
            )
        for path in ro_paths:
            rules_ok = (
                _add_path_rule(libc, add_rule_nr, ruleset_fd, path, ACCESS_FS_READ_ONLY)
                and rules_ok
            )

        # Exigido pelo kernel antes de landlock_restrict_self — prctl É
        # wrapado pelo glibc (diferente das 3 syscalls do Landlock).
        libc.prctl(_PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0)
        rc = libc.syscall(restrict_self_nr, ruleset_fd, 0)
        if rc != 0:
            logger.warning(
                "sandbox: landlock_restrict_self falhou (errno=%s) — seguindo "
                "sem Landlock",
                ctypes.get_errno(),
            )
            return False
        return rules_ok
    finally:
        os.close(ruleset_fd)

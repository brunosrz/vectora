"""Sandbox — backend.sandbox.landlock: wrapper ctypes das 3 syscalls do
Landlock LSM (sem glibc wrapper — man7.org/landlock_create_ruleset(2)).
Testes mockam ctypes/os (sem kernel Linux 5.13+ real disponível em CI/
dev nesta máquina) — cobrem a lógica de orquestração e degradação."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from backend.sandbox import landlock


@pytest.fixture(autouse=True)
def _ensure_linux_os_constants(monkeypatch):
    # O_PATH/O_CLOEXEC só existem em `os` no Linux — este dev roda em
    # Windows, então garantimos que os testes exercitam a lógica real do
    # módulo (que roda em Linux/WSL2 em produção) sem depender do SO local.
    monkeypatch.setattr(
        landlock.os, "O_PATH", getattr(landlock.os, "O_PATH", 0o10000000), raising=False
    )
    monkeypatch.setattr(
        landlock.os,
        "O_CLOEXEC",
        getattr(landlock.os, "O_CLOEXEC", 0o2000000),
        raising=False,
    )


def _fake_libc(create_rc=3, add_rule_rc=0, restrict_rc=0):
    """`syscall()` mockado — dispatcha pelo primeiro arg (número da
    syscall) igual ao `_SYSCALL_NUMBERS["x86_64"]` real."""
    create_nr, add_rule_nr, restrict_nr = landlock._SYSCALL_NUMBERS["x86_64"]

    def _syscall(nr, *args):
        if nr == create_nr:
            return create_rc
        if nr == add_rule_nr:
            return add_rule_rc
        if nr == restrict_nr:
            return restrict_rc
        raise AssertionError(f"syscall inesperada: {nr}")

    libc = MagicMock()
    libc.syscall.side_effect = _syscall
    libc.prctl = MagicMock()
    return libc


def test_arquitetura_nao_mapeada_degrada_sem_chamar_syscall(monkeypatch):
    monkeypatch.setattr(landlock.platform, "machine", lambda: "riscv64")

    result = landlock.apply_landlock(rw_paths=["/ws"], ro_paths=[])

    assert result is False


def test_happy_path_aplica_regras_e_restringe(monkeypatch, tmp_path):
    monkeypatch.setattr(landlock.platform, "machine", lambda: "x86_64")
    libc = _fake_libc()
    monkeypatch.setattr(landlock.ctypes, "CDLL", lambda *_a, **_k: libc)
    monkeypatch.setattr(landlock.ctypes, "get_errno", lambda: 0)
    monkeypatch.setattr(landlock.os, "open", lambda *_a, **_k: 7)
    close_mock = MagicMock()
    monkeypatch.setattr(landlock.os, "close", close_mock)

    result = landlock.apply_landlock(rw_paths=[str(tmp_path)], ro_paths=["/usr"])

    assert result is True
    libc.prctl.assert_called_once_with(landlock._PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0)
    # ruleset_fd (3) fechado no final, além do parent_fd (7) de cada regra.
    assert close_mock.call_count == 3  # 2 paths (rw+ro) + ruleset_fd


def test_create_ruleset_falhando_retorna_false_sem_lancar(monkeypatch):
    monkeypatch.setattr(landlock.platform, "machine", lambda: "x86_64")
    libc = _fake_libc(create_rc=-1)
    monkeypatch.setattr(landlock.ctypes, "CDLL", lambda *_a, **_k: libc)
    monkeypatch.setattr(landlock.ctypes, "get_errno", lambda: 38)  # ENOSYS

    result = landlock.apply_landlock(rw_paths=["/ws"], ro_paths=[])

    assert result is False
    libc.prctl.assert_not_called()


def test_restrict_self_falhando_retorna_false(monkeypatch, tmp_path):
    monkeypatch.setattr(landlock.platform, "machine", lambda: "x86_64")
    libc = _fake_libc(restrict_rc=1)
    monkeypatch.setattr(landlock.ctypes, "CDLL", lambda *_a, **_k: libc)
    monkeypatch.setattr(landlock.ctypes, "get_errno", lambda: 1)
    monkeypatch.setattr(landlock.os, "open", lambda *_a, **_k: 7)
    monkeypatch.setattr(landlock.os, "close", MagicMock())

    result = landlock.apply_landlock(rw_paths=[str(tmp_path)], ro_paths=[])

    assert result is False


def test_path_inexistente_e_ignorado_sem_quebrar_o_resto(monkeypatch, tmp_path):
    # Erro/borda: um rw_path que não existe no sistema (ex. path já
    # removido) não deve impedir as outras regras nem o restrict_self.
    monkeypatch.setattr(landlock.platform, "machine", lambda: "x86_64")
    libc = _fake_libc()
    monkeypatch.setattr(landlock.ctypes, "CDLL", lambda *_a, **_k: libc)
    monkeypatch.setattr(landlock.ctypes, "get_errno", lambda: 0)

    def _fake_open(path, _flags):
        if path == "/nao/existe":
            raise OSError("no such file")
        return 7

    monkeypatch.setattr(landlock.os, "open", _fake_open)
    monkeypatch.setattr(landlock.os, "close", MagicMock())

    result = landlock.apply_landlock(
        rw_paths=["/nao/existe", str(tmp_path)], ro_paths=[]
    )

    assert result is True


def test_add_rule_falhando_pra_um_path_nao_impede_restrict_self(monkeypatch, tmp_path):
    # add_rule falhar pra 1 path é um aviso, não motivo pra abortar o
    # resto — o processo ainda fica mais restrito do que sem Landlock.
    monkeypatch.setattr(landlock.platform, "machine", lambda: "x86_64")
    libc = _fake_libc(add_rule_rc=1)
    monkeypatch.setattr(landlock.ctypes, "CDLL", lambda *_a, **_k: libc)
    monkeypatch.setattr(landlock.ctypes, "get_errno", lambda: 1)
    monkeypatch.setattr(landlock.os, "open", lambda *_a, **_k: 7)
    monkeypatch.setattr(landlock.os, "close", MagicMock())

    result = landlock.apply_landlock(rw_paths=[str(tmp_path)], ro_paths=[])

    # rules_ok=False (a regra falhou) mas restrict_self ainda roda.
    assert result is False
    libc.syscall.assert_any_call(
        landlock._SYSCALL_NUMBERS["x86_64"][2],
        3,
        0,
    )


def test_access_fs_read_only_nao_inclui_write_nem_make(tmp_path):
    assert landlock.ACCESS_FS_READ_ONLY & landlock._ACCESS_FS_WRITE_FILE == 0
    assert landlock.ACCESS_FS_READ_ONLY & landlock._ACCESS_FS_MAKE_REG == 0
    assert landlock.ACCESS_FS_READ_ONLY & landlock._ACCESS_FS_READ_FILE != 0


def test_access_fs_v1_all_inclui_todos_os_13_direitos():
    bits = [1 << i for i in range(13)]
    combined = 0
    for b in bits:
        combined |= b
    assert combined == landlock.ACCESS_FS_V1_ALL

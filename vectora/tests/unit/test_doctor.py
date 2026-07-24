"""``vectora doctor`` — encontra e limpa sidecars nats-server órfãos por nome
de imagem (não só os PIDs conhecidos pelo pid file de nats_sidecar.py)."""

from __future__ import annotations

import argparse
from unittest.mock import MagicMock, patch

from backend.cli import doctor


def _run(stdout: str, returncode: int = 0) -> MagicMock:
    result = MagicMock()
    result.stdout = stdout
    result.returncode = returncode
    return result


class TestFindNatsServerPidsWin32:
    def test_parsing_feliz_da_saida_do_tasklist(self, monkeypatch):
        monkeypatch.setattr(doctor.sys, "platform", "win32")
        tasklist_output = (
            "nats-server.exe             12345 Console                    1      6.676 K\n"
            "nats-server.exe              9999 Console                    1      6.548 K\n"
        )
        with (
            patch.object(
                doctor.shutil, "which", return_value="C:\\Windows\\tasklist.exe"
            ),
            patch.object(doctor.subprocess, "run", return_value=_run(tasklist_output)),
        ):
            pids = doctor.find_nats_server_pids()

        assert pids == [12345, 9999]

    def test_tasklist_ausente_retorna_lista_vazia(self, monkeypatch):
        monkeypatch.setattr(doctor.sys, "platform", "win32")
        with patch.object(doctor.shutil, "which", return_value=None):
            assert doctor.find_nats_server_pids() == []

    def test_subprocess_lancando_retorna_lista_vazia(self, monkeypatch):
        # Erro/borda: qualquer falha do subprocess (timeout, permissão)
        # nunca deve propagar — degrada pra "nada encontrado".
        monkeypatch.setattr(doctor.sys, "platform", "win32")
        with (
            patch.object(doctor.shutil, "which", return_value="tasklist"),
            patch.object(doctor.subprocess, "run", side_effect=OSError("boom")),
        ):
            assert doctor.find_nats_server_pids() == []

    def test_saida_sem_processos_retorna_lista_vazia(self, monkeypatch):
        monkeypatch.setattr(doctor.sys, "platform", "win32")
        with (
            patch.object(doctor.shutil, "which", return_value="tasklist"),
            patch.object(
                doctor.subprocess,
                "run",
                return_value=_run("INFO: No tasks are running...\n"),
            ),
        ):
            assert doctor.find_nats_server_pids() == []


class TestFindNatsServerPidsPosix:
    def test_parsing_feliz_da_saida_do_pgrep(self, monkeypatch):
        monkeypatch.setattr(doctor.sys, "platform", "linux")
        with (
            patch.object(doctor.shutil, "which", return_value="/usr/bin/pgrep"),
            patch.object(doctor.subprocess, "run", return_value=_run("111\n222\n")),
        ):
            pids = doctor.find_nats_server_pids()

        assert pids == [111, 222]

    def test_pgrep_ausente_retorna_lista_vazia(self, monkeypatch):
        monkeypatch.setattr(doctor.sys, "platform", "linux")
        with patch.object(doctor.shutil, "which", return_value=None):
            assert doctor.find_nats_server_pids() == []


class TestRunDoctor:
    def test_sem_orfaos_nao_mata_nada(self, capsys):
        with (
            patch.object(doctor, "find_nats_server_pids", return_value=[]),
            patch("backend.scheduling.nats_sidecar.kill_orphan_pid") as kill_mock,
        ):
            doctor.run_doctor(argparse.Namespace(yes=False))

        kill_mock.assert_not_called()

    def test_com_yes_mata_sem_perguntar(self):
        with (
            patch.object(doctor, "find_nats_server_pids", return_value=[111, 222]),
            patch("backend.scheduling.nats_sidecar.kill_orphan_pid") as kill_mock,
        ):
            doctor.run_doctor(argparse.Namespace(yes=True))

        assert kill_mock.call_count == 2
        kill_mock.assert_any_call(111)
        kill_mock.assert_any_call(222)

    def test_sem_yes_recusa_confirmacao_nao_mata(self):
        # Erro/borda: resposta diferente de y/yes/s/sim cancela, sem matar.
        with (
            patch.object(doctor, "find_nats_server_pids", return_value=[111]),
            patch("builtins.input", return_value="n"),
            patch("backend.scheduling.nats_sidecar.kill_orphan_pid") as kill_mock,
        ):
            doctor.run_doctor(argparse.Namespace(yes=False))

        kill_mock.assert_not_called()

    def test_sem_yes_confirma_e_mata(self):
        with (
            patch.object(doctor, "find_nats_server_pids", return_value=[111]),
            patch("builtins.input", return_value="y"),
            patch("backend.scheduling.nats_sidecar.kill_orphan_pid") as kill_mock,
        ):
            doctor.run_doctor(argparse.Namespace(yes=False))

        kill_mock.assert_called_once_with(111)

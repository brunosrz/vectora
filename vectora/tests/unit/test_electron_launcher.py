"""Tests for backend/services/electron_launcher.py."""

from __future__ import annotations

from pathlib import Path

import pytest

from backend.services import electron_launcher


class TestResolveElectronLaunch:
    def test_sem_main_js_retorna_none(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(electron_launcher, "_electron_dir", lambda: tmp_path)
        assert electron_launcher.resolve_electron_launch() is None

    def test_sem_path_txt_retorna_none(self, tmp_path: Path, monkeypatch):
        (tmp_path / "dist").mkdir()
        (tmp_path / "dist" / "main.js").write_text("// main", encoding="utf-8")
        monkeypatch.setattr(electron_launcher, "_electron_dir", lambda: tmp_path)
        assert electron_launcher.resolve_electron_launch() is None

    def test_path_txt_vazio_retorna_none(self, tmp_path: Path, monkeypatch):
        (tmp_path / "dist").mkdir()
        (tmp_path / "dist" / "main.js").write_text("// main", encoding="utf-8")
        node_electron = tmp_path / "node_modules" / "electron"
        node_electron.mkdir(parents=True)
        (node_electron / "path.txt").write_text("", encoding="utf-8")
        monkeypatch.setattr(electron_launcher, "_electron_dir", lambda: tmp_path)
        assert electron_launcher.resolve_electron_launch() is None

    def test_binario_referenciado_nao_existe_retorna_none(
        self, tmp_path: Path, monkeypatch
    ):
        # Par de erro: path.txt aponta para um executável que não foi
        # baixado (dist/ do pacote electron incompleto) — nunca lança.
        (tmp_path / "dist").mkdir()
        (tmp_path / "dist" / "main.js").write_text("// main", encoding="utf-8")
        node_electron = tmp_path / "node_modules" / "electron"
        node_electron.mkdir(parents=True)
        (node_electron / "path.txt").write_text("electron.exe", encoding="utf-8")
        monkeypatch.setattr(electron_launcher, "_electron_dir", lambda: tmp_path)
        assert electron_launcher.resolve_electron_launch() is None

    def test_tudo_presente_resolve_executavel_e_main_js(
        self, tmp_path: Path, monkeypatch
    ):
        (tmp_path / "dist").mkdir()
        main_js = tmp_path / "dist" / "main.js"
        main_js.write_text("// main", encoding="utf-8")
        node_electron_dist = tmp_path / "node_modules" / "electron" / "dist"
        node_electron_dist.mkdir(parents=True)
        (node_electron_dist.parent / "path.txt").write_text(
            "electron.exe", encoding="utf-8"
        )
        exe = node_electron_dist / "electron.exe"
        exe.write_bytes(b"fake binary")
        monkeypatch.setattr(electron_launcher, "_electron_dir", lambda: tmp_path)

        result = electron_launcher.resolve_electron_launch()

        assert result == (str(exe), [str(main_js)])


@pytest.mark.skipif(
    not electron_launcher.resolve_electron_launch(),
    reason="build de dev do Electron ausente — rode `pnpm --dir electron install && "
    "pnpm --dir electron build`",
)
def test_resolve_no_repo_real_aponta_para_arquivos_que_existem():
    result = electron_launcher.resolve_electron_launch()
    assert result is not None
    exe, args = result
    assert Path(exe).is_file()
    assert len(args) == 1
    assert Path(args[0]).is_file()

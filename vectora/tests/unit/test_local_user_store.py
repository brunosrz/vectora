"""Persistência app-owned do usuário local (nome/empresa) fora do .env."""

from __future__ import annotations

from pathlib import Path

import backend.services.local_user as lu


def test_roundtrip(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(lu, "_FILE", tmp_path / "local_user.json")
    lu.write_local_user("Bruno", "Vectora")
    assert lu.read_local_user() == {"name": "Bruno", "company": "Vectora"}


def test_ausente_devolve_vazio(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(lu, "_FILE", tmp_path / "nao_existe.json")
    assert lu.read_local_user() == {"name": "", "company": ""}


def test_json_corrompido_degrada_sem_crash(tmp_path: Path, monkeypatch):
    f = tmp_path / "local_user.json"
    f.write_text("{lixo", encoding="utf-8")
    monkeypatch.setattr(lu, "_FILE", f)
    assert lu.read_local_user() == {"name": "", "company": ""}


def test_nao_escreve_no_env(tmp_path: Path, monkeypatch):
    # Garante que a persistência é o JSON, não um .env.
    target = tmp_path / "local_user.json"
    monkeypatch.setattr(lu, "_FILE", target)
    lu.write_local_user("Ada", "")
    assert target.exists()
    assert not (tmp_path / ".env").exists()

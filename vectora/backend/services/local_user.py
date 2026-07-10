"""Persistência app-owned do usuário local (nome/empresa) — fora do ``.env``.

O ``.env`` guarda só segredo (API keys). Nome e empresa do usuário local são
dados não-secretos e ficam em ``~/.vectora/local_user.json`` (app-owned,
sobrevive a restart, fora do repositório).
"""

from __future__ import annotations

import json
from pathlib import Path

_FILE = Path.home() / ".vectora" / "local_user.json"


def read_local_user() -> dict[str, str]:
    """Lê ``{name, company}`` do JSON; devolve strings vazias se ausente/inválido."""
    try:
        data = json.loads(_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"name": "", "company": ""}
    if not isinstance(data, dict):
        return {"name": "", "company": ""}
    return {
        "name": str(data.get("name", "")),
        "company": str(data.get("company", "")),
    }


def write_local_user(name: str, company: str) -> None:
    """Grava ``{name, company}`` no JSON app-owned (cria a pasta se preciso)."""
    _FILE.parent.mkdir(parents=True, exist_ok=True)
    _FILE.write_text(
        json.dumps({"name": name, "company": company}, ensure_ascii=False),
        encoding="utf-8",
    )

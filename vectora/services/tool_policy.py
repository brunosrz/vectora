"""Política de tools por usuário — ABAC simples (Bloco S, S5).

Cada usuário tem uma lista de tools desabilitadas, persistida em
``~/.vectora/tools/<user_id>.json``. Por padrão, todas as tools são permitidas
(allow-all). Admin/root e o próprio usuário podem desabilitar tools; a resolução
de toolset (``tool_resolver``) consulta esta política a cada request.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

#: Contador de versão por usuário — bumpado em set_disabled, invalida o cache
#: do LLM bindado sem reiniciar.
_versions: dict[str, int] = {}


def policy_version(user_id: str) -> int:
    """Versão atual da política de tools do usuário (muda em set_disabled)."""
    return _versions.get(user_id, 0)


def _policy_dir() -> Path:
    return Path.home() / ".vectora" / "tools"


def _user_file(user_id: str) -> Path:
    safe = (user_id or "local").replace("/", "_").replace("\\", "_")
    return _policy_dir() / f"{safe}.json"


def get_disabled(user_id: str) -> list[str]:
    """Lista de nomes de tools desabilitadas para o usuário."""
    path = _user_file(user_id)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        disabled = data.get("disabled", [])
        return [str(n) for n in disabled]
    except Exception:
        logger.warning("tool_policy: arquivo inválido para %s", user_id)
        return []


def set_disabled(user_id: str, names: list[str]) -> None:
    """Define o conjunto de tools desabilitadas do usuário (substitui)."""
    path = _user_file(user_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"disabled": sorted(set(names))}
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    _versions[user_id] = _versions.get(user_id, 0) + 1


def is_allowed(user_id: str, tool_name: str) -> bool:
    """True se a tool está permitida para o usuário (allow-all por padrão)."""
    return tool_name not in set(get_disabled(user_id))

"""Política de tools por usuário — ABAC simples.

Cada usuário tem uma lista de tools desabilitadas, persistida em
``~/.vectora/tools/<user_id>.json``. Por padrão, todas as tools são permitidas
(allow-all). Admin/root e o próprio usuário podem desabilitar tools; a resolução
de toolset (``tool_resolver``) consulta esta política a cada request.

``GLOBAL_SCOPE`` é um "usuário" virtual: o kill-switch do admin
(``POST /admin/tools/{name}/toggle``) grava nele, reaproveitando o mesmo
arquivo/versionamento/pubsub — não é um usuário real e nunca aparece em
``/admin/users``. ``is_allowed`` nega se a tool estiver desabilitada
globalmente OU para o usuário específico.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from backend.settings import settings

logger = logging.getLogger(__name__)

#: "Usuário" virtual para o disable global (admin kill-switch), aplicado a
#: todas as sessões independente de user_id — ver módulo docstring.
GLOBAL_SCOPE = "__global__"

#: Contador de versão por usuário — bumpado em set_disabled, invalida o cache
#: do LLM bindado sem reiniciar.
_versions: dict[str, int] = {}


def policy_version(user_id: str) -> int:
    """Versão atual da política de tools do usuário (muda em set_disabled)."""
    return _versions.get(user_id, 0)


def _policy_dir() -> Path:
    return settings.vectora_home / "tools"


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
    # Avisa as demais réplicas — no modo lite é um no-op local.
    from backend.persistence.kv import publish_soon

    publish_soon(
        "vectora:policy",
        json.dumps({"user_id": user_id, "version": _versions[user_id]}),
    )


def apply_remote_version(user_id: str, version: int) -> None:
    """Aplica um bump de versão vindo de outra réplica (via cache_sync).

    A política em si vive em arquivo (relido a cada request); avançar a
    versão local basta para invalidar o LLM bindado, cuja chave a inclui.
    """
    if version > _versions.get(user_id, 0):
        _versions[user_id] = version


def is_allowed(user_id: str, tool_name: str) -> bool:
    """True se a tool está permitida (nem globalmente, nem para o usuário)."""
    if tool_name in set(get_disabled(GLOBAL_SCOPE)):
        return False
    return tool_name not in set(get_disabled(user_id))


def effective_disabled(user_id: str | None) -> set[str]:
    """União do disable global (admin) com o do usuário (ABAC), se houver."""
    disabled = set(get_disabled(GLOBAL_SCOPE))
    if user_id:
        disabled |= set(get_disabled(user_id))
    return disabled

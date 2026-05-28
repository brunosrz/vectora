"""Serviço de permissões e RBAC do Vectora.

Define a hierarquia de roles e as regras de acesso por recurso/ação.
Todas as verificações são fail-closed (negam por padrão).

Hierarquia de roles (maior índice = mais permissões):
    viewer  (0)  — leitura em workspaces compartilhados
    member  (1)  — threads/workspace próprios, RAG, terminal restrito
    admin   (2)  — threads de terceiros, audit log, workspaces compartilhados
    root    (3)  — tudo (igual admin + mudar roles, deletar root)
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import HTTPException

logger = logging.getLogger(__name__)

_ROLE_LEVEL: dict[str, int] = {
    "viewer": 0,
    "member": 1,
    "admin": 2,
    "root": 3,
}


def role_level(role: str) -> int:
    """Retorna o nível numérico do role (maior = mais permissões)."""
    return _ROLE_LEVEL.get(role, -1)


def has_min_role(user: Any, min_role: str) -> bool:
    """True se o usuário tem pelo menos o role mínimo exigido."""
    if user is None:
        return False
    return role_level(getattr(user, "role", "")) >= role_level(min_role)


def require_min_role(user: Any, min_role: str) -> None:
    """Lança HTTPException 403 se o usuário não tiver o role mínimo."""
    if not has_min_role(user, min_role):
        raise HTTPException(
            status_code=403,
            detail=f"Requer role '{min_role}' ou superior.",
        )


def can_access_thread(user: Any, thread_owner_id: str | None) -> bool:
    """True se o usuário pode ler/escrever na thread.

    - root e admin: qualquer thread
    - member/viewer: apenas threads próprias
    """
    if user is None:
        return False
    if has_min_role(user, "admin"):
        return True
    return thread_owner_id is None or thread_owner_id == user.id


def can_delete_thread(user: Any, thread_owner_id: str | None) -> bool:
    """True se o usuário pode deletar a thread."""
    if user is None:
        return False
    if has_min_role(user, "admin"):
        return True
    return thread_owner_id == user.id


def can_run_terminal(user: Any, workspace_owner_id: str | None) -> bool:
    """True se o usuário pode executar comandos de terminal no workspace.

    - root/admin: qualquer workspace
    - member: apenas workspace próprio
    - viewer: nunca
    """
    if user is None:
        return False
    if has_min_role(user, "admin"):
        return True
    if user.role == "member":
        return workspace_owner_id is None or workspace_owner_id == user.id
    return False


def can_read_audit(user: Any) -> bool:
    """True se o usuário pode ver o audit log completo."""
    return has_min_role(user, "admin")


def can_manage_users(user: Any) -> bool:
    """True se o usuário pode criar/deletar/modificar outros usuários."""
    return has_min_role(user, "root")

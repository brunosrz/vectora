"""Handler do painel de administração — Bloco P.

Endpoints (todos exigem role admin ou root):
    GET    /admin/users                      — lista todos os usuários
    GET    /admin/users/{user_id}            — detalhes de um usuário
    PATCH  /admin/users/{user_id}/role       — muda role de um usuário
    DELETE /admin/users/{user_id}            — remove usuário (root only)
    GET    /admin/tools                      — tools disponíveis e status
    POST   /admin/tools/{tool_name}/toggle   — habilita/desabilita tool globalmente
    GET    /admin/system                     — versão, status dos serviços, métricas
    GET    /admin/config                     — configurações globais do servidor
    PATCH  /admin/config                     — atualiza configurações globais
"""

from __future__ import annotations

import logging
import platform
import sys
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])

# ---------------------------------------------------------------------------
# Helpers de autorização
# ---------------------------------------------------------------------------

_ADMIN_ROLES = {"root", "admin"}
_ROOT_ONLY_ROLES = {"root"}


def require_admin(user: Any) -> None:
    """Lança HTTPException 403 se user não é admin ou root."""
    role = getattr(user, "role", None)
    if role not in _ADMIN_ROLES:
        raise HTTPException(
            status_code=403,
            detail=f"Acesso negado. Role '{role}' não tem permissão de administrador.",
        )


def require_root(user: Any) -> None:
    """Lança HTTPException 403 se user não é root."""
    role = getattr(user, "role", None)
    if role not in _ROOT_ONLY_ROLES:
        raise HTTPException(
            status_code=403,
            detail="Acesso negado. Apenas root pode executar esta ação.",
        )


def _get_user(request: Request) -> Any:
    user = getattr(request.state, "user", None)
    if user is None:
        raise HTTPException(status_code=401, detail="Não autenticado")
    return user


# ---------------------------------------------------------------------------
# Helpers de informação do sistema
# ---------------------------------------------------------------------------


def _build_system_info() -> dict[str, Any]:
    """Constrói o dicionário de informações do sistema."""
    try:
        from vectora.version import __version__

        version = __version__
    except Exception:
        version = "unknown"

    return {
        "version": version,
        "python_version": sys.version,
        "platform": platform.platform(),
        "architecture": platform.machine(),
    }


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class UpdateRoleBody(BaseModel):
    role: str


class ToolToggleBody(BaseModel):
    enabled: bool


class PatchConfigBody(BaseModel):
    allow_public_signup: bool | None = None
    default_model: str | None = None
    max_recursion: int | None = None


# ---------------------------------------------------------------------------
# P2 — Endpoints de administração
# ---------------------------------------------------------------------------


@router.get("/users")
async def list_users(request: Request) -> dict:
    """Lista todos os usuários cadastrados com stats básicos."""
    user = _get_user(request)
    require_admin(user)

    try:
        from vectora.services import auth as auth_svc

        users = await auth_svc.list_users()
        return {
            "users": [
                {
                    "id": u.id,
                    "email": u.email,
                    "role": u.role,
                    "created_at": str(u.created_at),
                    "last_login_at": str(u.last_login_at)
                    if getattr(u, "last_login_at", None)
                    else None,
                }
                for u in users
            ],
            "total": len(users),
        }
    except Exception as exc:
        logger.exception("list_users failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/users/{user_id}")
async def get_user_detail(request: Request, user_id: str) -> dict:
    """Detalhes de um usuário específico."""
    user = _get_user(request)
    require_admin(user)

    try:
        from vectora.services import auth as auth_svc

        target = await auth_svc.get_user_by_id(user_id)
        if target is None:
            raise HTTPException(status_code=404, detail="Usuário não encontrado")

        overrides = await auth_svc.get_env_overrides(user_id)
        # Nunca expõe valores — apenas as chaves
        env_keys = list(overrides.keys())

        return {
            "id": target.id,
            "email": target.email,
            "role": target.role,
            "created_at": str(target.created_at),
            "last_login_at": str(target.last_login_at)
            if getattr(target, "last_login_at", None)
            else None,
            "env_keys": env_keys,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("get_user_detail failed: user_id=%s", user_id)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.patch("/users/{user_id}/role")
async def update_user_role(
    request: Request, user_id: str, body: UpdateRoleBody
) -> dict:
    """Muda o role de um usuário. Apenas root pode promover a root."""
    user = _get_user(request)
    require_admin(user)

    # Promover para root exige ser root
    if body.role == "root":
        require_root(user)

    valid_roles = {"root", "admin", "member", "viewer"}
    if body.role not in valid_roles:
        raise HTTPException(
            status_code=400,
            detail=f"Role inválido. Valores válidos: {sorted(valid_roles)}",
        )

    try:
        from vectora.services import auth as auth_svc

        await auth_svc.update_user_role(user_id, body.role)
        return {"status": "updated", "user_id": user_id, "role": body.role}
    except Exception as exc:
        logger.exception("update_user_role failed: user_id=%s", user_id)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.delete("/users/{user_id}")
async def delete_user(request: Request, user_id: str) -> dict:
    """Remove um usuário. Apenas root pode deletar usuários."""
    user = _get_user(request)
    require_root(user)

    if user.id == user_id:
        raise HTTPException(status_code=400, detail="Você não pode deletar a si mesmo.")

    try:
        from vectora.services import auth as auth_svc

        await auth_svc.delete_user(user_id)
        return {"status": "deleted", "user_id": user_id}
    except Exception as exc:
        logger.exception("delete_user failed: user_id=%s", user_id)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/tools")
async def list_tools_admin(request: Request) -> dict:
    """Lista todas as tools com status de habilitação global."""
    user = _get_user(request)
    require_admin(user)

    try:
        from vectora.nodes.tools import ALL_TOOLS

        tools = [
            {
                "name": t.name,
                "description": t.description or "",
                "category": (getattr(t, "metadata", None) or {}).get(
                    "category", "general"
                ),
                "destructive": bool(
                    (getattr(t, "metadata", None) or {}).get("destructive", False)
                ),
                "enabled": True,  # TODO: persistir overrides por tool em config.toml
            }
            for t in ALL_TOOLS
        ]
        return {"tools": tools, "total": len(tools)}
    except Exception as exc:
        logger.exception("list_tools_admin failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/tools/{tool_name}/toggle")
async def toggle_tool(request: Request, tool_name: str, body: ToolToggleBody) -> dict:
    """Habilita ou desabilita uma tool globalmente."""
    user = _get_user(request)
    require_admin(user)
    # TODO: persistir em config.toml quando o gerenciamento de config for implementado
    logger.info(
        "admin: tool '%s' %s por user_id=%s",
        tool_name,
        "habilitada" if body.enabled else "desabilitada",
        user.id,
    )
    return {"status": "ok", "tool": tool_name, "enabled": body.enabled}


@router.get("/system")
async def system_info(request: Request) -> dict:
    """Retorna versão, status dos serviços e métricas básicas."""
    user = _get_user(request)
    require_admin(user)

    info = _build_system_info()

    # Status dos serviços
    services: dict[str, str] = {}
    try:
        import aiosqlite  # noqa: F401

        services["sqlite"] = "ok"
    except Exception:
        services["sqlite"] = "unavailable"

    try:
        import lancedb  # noqa: F401

        services["lancedb"] = "ok"
    except Exception:
        services["lancedb"] = "unavailable"

    # Métricas recentes do tracer
    recent_spans: list = []
    try:
        from vectora.services.tracer import tracer

        recent_spans = await tracer.get_recent(n=20)
    except Exception:
        pass

    return {
        **info,
        "services": services,
        "recent_spans_count": len(recent_spans),
    }


@router.get("/config")
async def get_server_config(request: Request) -> dict:
    """Retorna as configurações globais do servidor."""
    user = _get_user(request)
    require_admin(user)

    try:
        from vectora.config.settings import settings

        return {
            "default_model": getattr(settings, "default_model", ""),
            "max_recursion": getattr(settings, "max_recursion", 50),
            "allow_public_signup": getattr(settings, "allow_public_signup", False),
            "db_dsn": getattr(settings, "db_dsn", ""),
        }
    except Exception as exc:
        logger.exception("get_server_config failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.patch("/config")
async def patch_server_config(request: Request, body: PatchConfigBody) -> dict:
    """Atualiza configurações globais do servidor em runtime."""
    user = _get_user(request)
    require_root(user)

    # Runtime-only patch — alterações não sobrevivem a restart sem config.toml
    # TODO: persistir em ~/.vectora/config.toml
    updated: dict[str, Any] = {}
    try:
        from vectora.config.settings import settings

        if body.allow_public_signup is not None:
            settings.allow_public_signup = body.allow_public_signup  # type: ignore[attr-defined]
            updated["allow_public_signup"] = body.allow_public_signup

        if body.default_model is not None:
            settings.default_model = body.default_model  # type: ignore[attr-defined]
            updated["default_model"] = body.default_model

        if body.max_recursion is not None:
            settings.max_recursion = body.max_recursion  # type: ignore[attr-defined]
            updated["max_recursion"] = body.max_recursion

        logger.info("admin: config patched by root user_id=%s: %s", user.id, updated)
        return {"status": "updated", "updated": updated}
    except Exception as exc:
        logger.exception("patch_server_config failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

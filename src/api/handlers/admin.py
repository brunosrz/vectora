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
import os
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
        from src.version import __version__

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


class CreateInviteBody(BaseModel):
    role: str = "member"
    email: str | None = None
    ttl_hours: int = 24


class ToolOverrideBody(BaseModel):
    disabled: list[str] = []


class PatchConfigBody(BaseModel):
    allow_public_signup: bool | None = None
    default_model: str | None = None
    max_recursion: int | None = None
    # `vectora_token`: token de licença do produto. Persiste em
    # `~/.vectora/config.toml`; aplica imediatamente no `os.environ`,
    # mas o `LicenseStatusInfo` cacheado só renova no próximo
    # `validate_license_*` (TTL 6h ou após restart).
    vectora_token: str | None = None


class CreateSafeRootBody(BaseModel):
    path: str
    label: str = ""


class UpdateSafeRootBody(BaseModel):
    label: str


# ---------------------------------------------------------------------------
# P2 — Endpoints de administração
# ---------------------------------------------------------------------------


@router.get("/users")
async def list_users(request: Request) -> dict:
    """Lista todos os usuários cadastrados com stats básicos."""
    user = _get_user(request)
    require_admin(user)

    try:
        from src.services import auth as auth_svc

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
        from src.services import auth as auth_svc

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
        from src.services import auth as auth_svc

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
        from src.services import auth as auth_svc

        await auth_svc.delete_user(user_id)
        return {"status": "deleted", "user_id": user_id}
    except Exception as exc:
        logger.exception("delete_user failed: user_id=%s", user_id)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/users/{user_id}/tools")
async def get_user_tools(request: Request, user_id: str) -> dict:
    """Política de tools de um usuário (override ABAC — P2/S5)."""
    user = _get_user(request)
    require_admin(user)
    from src.nodes.tools import ALL_TOOLS
    from src.services import tool_policy

    return {
        "disabled": tool_policy.get_disabled(user_id),
        "available": [t.name for t in ALL_TOOLS],
    }


@router.post("/users/{user_id}/tools")
async def set_user_tools(
    request: Request, user_id: str, body: ToolOverrideBody
) -> dict:
    """Define as tools desabilitadas de um usuário (admin override)."""
    user = _get_user(request)
    require_admin(user)
    from src.nodes.tools import ALL_TOOLS
    from src.services import tool_policy

    valid = {t.name for t in ALL_TOOLS}
    unknown = [n for n in body.disabled if n not in valid]
    if unknown:
        raise HTTPException(
            status_code=400, detail=f"Tools desconhecidas: {sorted(unknown)}"
        )
    tool_policy.set_disabled(user_id, body.disabled)
    return {"status": "ok", "user_id": user_id, "disabled": body.disabled}


@router.post("/invites")
async def create_invite(request: Request, body: CreateInviteBody) -> dict:
    """Gera um link de convite de signup com token expirável."""
    import os

    user = _get_user(request)
    require_admin(user)

    valid_roles = {"admin", "member", "viewer"}
    if body.role not in valid_roles:
        raise HTTPException(
            status_code=400,
            detail=f"Role inválido para convite. Válidos: {sorted(valid_roles)}",
        )

    try:
        from typing import cast

        from src.services import auth as auth_svc
        from src.services.auth import Role

        token, expires_at = await auth_svc.create_invite(
            user.id,
            role=cast("Role", body.role),
            email=body.email,
            ttl_hours=body.ttl_hours,
        )
        frontend = os.environ.get("VECTORA_FRONTEND_URL", "http://localhost:3000")
        url = f"{frontend.rstrip('/')}/auth/signup?invite={token}"
        return {"token": token, "url": url, "expires_at": expires_at}
    except Exception as exc:
        logger.exception("create_invite failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/invites")
async def list_invites(request: Request) -> dict:
    """Lista convites pendentes (não usados, não expirados)."""
    user = _get_user(request)
    require_admin(user)

    try:
        from src.services import auth as auth_svc

        invites = await auth_svc.list_invites()
        return {"invites": invites, "total": len(invites)}
    except Exception as exc:
        logger.exception("list_invites failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.delete("/invites/{token_hash}")
async def revoke_invite(request: Request, token_hash: str) -> dict:
    """Revoga um convite pendente pelo seu hash."""
    user = _get_user(request)
    require_admin(user)

    try:
        from src.services import auth as auth_svc

        removed = await auth_svc.revoke_invite(token_hash)
        if not removed:
            raise HTTPException(status_code=404, detail="Convite não encontrado.")
        return {"status": "revoked", "token_hash": token_hash}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("revoke_invite failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/tools")
async def list_tools_admin(request: Request) -> dict:
    """Lista todas as tools com status de habilitação global."""
    user = _get_user(request)
    require_admin(user)

    try:
        from src.nodes.tools import ALL_TOOLS

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
        import aiosqlite

        services["sqlite"] = "ok"
    except Exception:
        services["sqlite"] = "unavailable"

    try:
        import lancedb

        services["lancedb"] = "ok"
    except Exception:
        services["lancedb"] = "unavailable"

    # Métricas recentes do tracer
    recent_spans: list = []
    try:
        from src.services.tracer import tracer

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
        from src.settings import settings

        raw_token = os.environ.get("VECTORA_TOKEN", "").strip()
        # Mostra prefixo + sufixo para o operador conferir sem expor o segredo.
        masked = (
            f"{raw_token[:7]}•••{raw_token[-4:]}"
            if len(raw_token) > 14
            else ("•" * 8 if raw_token else "")
        )

        return {
            "default_model": getattr(settings, "default_model", ""),
            "max_recursion": getattr(settings, "max_recursion", 50),
            "allow_public_signup": getattr(settings, "allow_public_signup", False),
            "db_dsn": getattr(settings, "db_dsn", ""),
            "vectora_token_masked": masked,
            "vectora_token_configured": bool(raw_token),
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
        from src.settings import settings

        if body.allow_public_signup is not None:
            settings.allow_public_signup = body.allow_public_signup  # type: ignore[attr-defined]  # ty: ignore[unresolved-attribute]
            updated["allow_public_signup"] = body.allow_public_signup

        if body.default_model is not None:
            settings.default_model = body.default_model  # type: ignore[attr-defined]  # ty: ignore[unresolved-attribute]
            updated["default_model"] = body.default_model

        if body.max_recursion is not None:
            settings.max_recursion = body.max_recursion  # type: ignore[attr-defined]  # ty: ignore[unresolved-attribute]
            updated["max_recursion"] = body.max_recursion

        if body.vectora_token is not None:
            token = body.vectora_token.strip()
            os.environ["VECTORA_TOKEN"] = token
            # Persiste em ~/.vectora/config.toml na seção [license] para
            # que o próximo boot do binário aplique sem o operador
            # precisar exportar a env var manualmente.
            from src.services.license import write_token_to_config

            write_token_to_config(token)
            updated["vectora_token_configured"] = bool(token)

        logger.info("admin: config patched by root user_id=%s: %s", user.id, updated)
        return {"status": "updated", "updated": updated}
    except Exception as exc:
        logger.exception("patch_server_config failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# F.3.3 — Pastas Seguras (SafeRoot)
# ---------------------------------------------------------------------------


@router.get("/safe-roots")
async def list_safe_roots_admin(request: Request) -> dict:
    """Lista as raízes confiáveis configuradas (admin)."""
    user = _get_user(request)
    require_admin(user)
    from src.services.safe_roots import get_safe_root_registry

    registry = get_safe_root_registry()
    return {
        "roots": [r.model_dump() for r in registry.all_roots()],
    }


@router.post("/safe-roots")
async def create_safe_root(request: Request, body: CreateSafeRootBody) -> dict:
    """Adiciona uma nova raiz confiável. Idempotente por path."""
    user = _get_user(request)
    require_admin(user)
    from pathlib import Path as _Path

    from src.services.safe_roots import get_safe_root_registry

    target = _Path(body.path).expanduser()
    try:
        target = target.resolve()
    except OSError as exc:
        raise HTTPException(status_code=400, detail=f"Path inválido: {exc}") from exc
    if not target.exists() or not target.is_dir():
        raise HTTPException(
            status_code=400,
            detail=f"Caminho não existe ou não é diretório: {target}",
        )

    registry = get_safe_root_registry()
    root = registry.add(str(target), body.label, str(user.id))
    logger.info(
        "admin: safe-root adicionado por user_id=%s path=%s label=%s",
        user.id,
        root.path,
        root.label,
    )
    return {"status": "created", "root": root.model_dump()}


@router.patch("/safe-roots/{root_id}")
async def update_safe_root(
    request: Request,
    root_id: str,
    body: UpdateSafeRootBody,
) -> dict:
    """Renomeia uma raiz confiável (label). Builtin aceita rename."""
    user = _get_user(request)
    require_admin(user)
    from src.services.safe_roots import get_safe_root_registry

    registry = get_safe_root_registry()
    updated = registry.update_label(root_id, body.label)
    if updated is None:
        raise HTTPException(status_code=404, detail="Raiz não encontrada")
    return {"status": "updated", "root": updated.model_dump()}


@router.delete("/safe-roots/{root_id}")
async def delete_safe_root(request: Request, root_id: str) -> dict:
    """Remove uma raiz confiável. Recusa se for builtin."""
    user = _get_user(request)
    require_admin(user)
    from src.services.safe_roots import get_safe_root_registry

    registry = get_safe_root_registry()
    root = registry.get(root_id)
    if root is None:
        raise HTTPException(status_code=404, detail="Raiz não encontrada")
    if root.builtin:
        raise HTTPException(
            status_code=400,
            detail="Raiz builtin não pode ser removida.",
        )
    ok = registry.remove(root_id)
    if not ok:
        raise HTTPException(status_code=500, detail="Falha ao remover")
    logger.info("admin: safe-root removido por user_id=%s path=%s", user.id, root.path)
    return {"status": "deleted"}

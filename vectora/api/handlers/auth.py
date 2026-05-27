"""Handler do serviço AuthService — autenticação e identidade via REST.

Endpoints:
    POST /auth/signup               — cria conta (primeiro vira root)
    POST /auth/signin               — login com email + senha
    POST /auth/refresh              — rotaciona tokens
    POST /auth/signout              — logout (revoga refresh token)
    GET  /auth/me                   — dados do usuário autenticado
    POST /auth/change-password      — troca senha (requer auth)
    GET  /auth/has-users            — setup wizard: false = primeiro acesso
    GET  /auth/users                — lista usuários (admin/root only)
    POST /auth/users/{id}/role      — muda role (root only)
    GET  /auth/audit                — audit log (admin/root only)
    GET  /auth/envs                 — env overrides do usuário autenticado
    POST /auth/envs                 — define env override
    DELETE /auth/envs/{key}         — remove env override
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request, Response

from vectora.api.schemas import (
    AuditEntry,
    ChangePasswordRequest,
    EnvOverrideRequest,
    HasUsersResponse,
    RefreshRequest,
    SigninRequest,
    SignoutRequest,
    SignupRequest,
    TokenResponse,
    UpdateRoleRequest,
    UserListResponse,
    UserResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

# Cookie names
_ACCESS_COOKIE = "vectora_access"
_REFRESH_COOKIE = "vectora_refresh"
_COOKIE_MAX_AGE_ACCESS = 15 * 60  # 15 min
_COOKIE_MAX_AGE_REFRESH = 7 * 24 * 3600  # 7 dias


def _set_auth_cookies(
    response: Response, access_token: str, refresh_token: str
) -> None:
    """Grava cookies httpOnly + SameSite=Strict nos dois tokens."""
    response.set_cookie(
        _ACCESS_COOKIE,
        access_token,
        max_age=_COOKIE_MAX_AGE_ACCESS,
        httponly=True,
        samesite="strict",
        secure=False,  # True em produção com HTTPS
    )
    response.set_cookie(
        _REFRESH_COOKIE,
        refresh_token,
        max_age=_COOKIE_MAX_AGE_REFRESH,
        httponly=True,
        samesite="strict",
        secure=False,
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(_ACCESS_COOKIE)
    response.delete_cookie(_REFRESH_COOKIE)


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else ""


# ---------------------------------------------------------------------------
# Endpoints públicos (sem auth)
# ---------------------------------------------------------------------------


@router.get("/has-users", response_model=HasUsersResponse)
async def has_users_endpoint() -> HasUsersResponse:
    """Retorna false quando a instância ainda não tem nenhum usuário.

    Usado pelo frontend para decidir se mostra signup ou signin na primeira
    visita. Após o primeiro signup, retorna sempre true.
    """
    from vectora.services.auth import has_users

    return HasUsersResponse(exists=await has_users())


@router.post("/signup", response_model=TokenResponse)
async def signup_endpoint(
    body: SignupRequest,
    request: Request,
    response: Response,
) -> TokenResponse:
    """Cria conta. O primeiro usuário vira root; os demais viram member.

    Retorna tokens via JSON e também os grava em cookies httpOnly.
    """
    from vectora.services import auth as auth_svc

    # Bloqueia signup público se já houver usuários e a config não permitir
    if await auth_svc.has_users():
        # Futuramente: ler allow_public_signup de config.toml
        # Por ora: bloqueia signup público após primeiro usuário
        # (admin/root pode criar usuários via POST /auth/users)
        raise HTTPException(
            status_code=403,
            detail="Signup público desabilitado. Contate o administrador.",
        )

    try:
        user, access_token, refresh_token = await auth_svc.signup(
            body.email, body.password
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    _set_auth_cookies(response, access_token, refresh_token)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.from_user(user),
    )


@router.post("/signin", response_model=TokenResponse)
async def signin_endpoint(
    body: SigninRequest,
    request: Request,
    response: Response,
) -> TokenResponse:
    from vectora.services import auth as auth_svc

    ip = _client_ip(request)
    try:
        user, access_token, refresh_token = await auth_svc.signin(
            body.email, body.password, ip=ip
        )
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    _set_auth_cookies(response, access_token, refresh_token)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.from_user(user),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_endpoint(
    body: RefreshRequest,
    request: Request,
    response: Response,
) -> TokenResponse:
    """Rotaciona tokens usando o refresh token do body ou do cookie."""
    from vectora.services import auth as auth_svc

    token = body.refresh_token or request.cookies.get(_REFRESH_COOKIE, "")
    if not token:
        raise HTTPException(status_code=401, detail="Refresh token não fornecido.")
    try:
        user, access_token, new_refresh = await auth_svc.refresh_tokens(token)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    _set_auth_cookies(response, access_token, new_refresh)
    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh,
        user=UserResponse.from_user(user),
    )


@router.post("/signout")
async def signout_endpoint(
    body: SignoutRequest,
    request: Request,
    response: Response,
) -> dict:
    from vectora.services import auth as auth_svc

    token = body.refresh_token or request.cookies.get(_REFRESH_COOKIE, "")
    if token:
        await auth_svc.signout(token)
    _clear_auth_cookies(response)
    return {}


# ---------------------------------------------------------------------------
# Endpoints protegidos (requerem auth — via middleware)
# ---------------------------------------------------------------------------


@router.get("/me", response_model=UserResponse)
async def me_endpoint(request: Request) -> UserResponse:
    user = getattr(request.state, "user", None)
    if user is None:
        raise HTTPException(status_code=401, detail="Não autenticado.")
    return UserResponse.from_user(user)


@router.post("/change-password")
async def change_password_endpoint(
    body: ChangePasswordRequest,
    request: Request,
    response: Response,
) -> dict:
    from vectora.services import auth as auth_svc

    user = getattr(request.state, "user", None)
    if user is None:
        raise HTTPException(status_code=401, detail="Não autenticado.")
    try:
        await auth_svc.change_password(user.id, body.old_password, body.new_password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Limpa cookies — próximo request precisa fazer signin novamente
    _clear_auth_cookies(response)
    return {"ok": True}


# ---------------------------------------------------------------------------
# Admin endpoints
# ---------------------------------------------------------------------------


@router.get("/users", response_model=UserListResponse)
async def list_users(request: Request) -> UserListResponse:
    from vectora.services.auth import get_db_for_audit
    from vectora.services.permissions import require_min_role

    user = getattr(request.state, "user", None)
    require_min_role(user, "admin")

    db = await get_db_for_audit()
    async with db.execute(
        "SELECT id, email, role, created_at, last_login_at FROM users ORDER BY created_at"
    ) as cur:
        rows = await cur.fetchall()

    users = [
        UserResponse(
            id=r["id"],
            email=r["email"],
            role=r["role"],
            created_at=r["created_at"],
            last_login_at=r["last_login_at"],
        )
        for r in rows
    ]
    return UserListResponse(users=users)


@router.post("/users/{user_id}/role")
async def update_role(user_id: str, body: UpdateRoleRequest, request: Request) -> dict:
    from vectora.services.auth import get_db_for_audit
    from vectora.services.permissions import require_min_role

    caller = getattr(request.state, "user", None)
    require_min_role(caller, "root")

    db = await get_db_for_audit()
    await db.execute("UPDATE users SET role = ? WHERE id = ?", (body.role, user_id))
    await db.commit()
    return {"ok": True}


@router.get("/audit", response_model=list[AuditEntry])
async def get_audit_log(
    request: Request,
    limit: int = 100,
    action: str | None = None,
    user_id: str | None = None,
) -> list[AuditEntry]:
    import json

    from vectora.services.auth import get_db_for_audit
    from vectora.services.permissions import require_min_role

    caller = getattr(request.state, "user", None)
    require_min_role(caller, "admin")

    db = await get_db_for_audit()
    query = "SELECT * FROM audit WHERE 1=1"
    params: list = []
    if action:
        query += " AND action = ?"
        params.append(action)
    if user_id:
        query += " AND user_id = ?"
        params.append(user_id)
    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(min(limit, 500))

    async with db.execute(query, params) as cur:
        rows = await cur.fetchall()

    return [
        AuditEntry(
            id=r["id"],
            user_id=r["user_id"],
            action=r["action"],
            target_type=r["target_type"],
            target_id=r["target_id"],
            timestamp=r["timestamp"],
            ip=r["ip"] or "",
            success=bool(r["success"]),
            metadata=json.loads(r["metadata_json"] or "{}"),
        )
        for r in rows
    ]


# ---------------------------------------------------------------------------
# Env overrides (C10)
# ---------------------------------------------------------------------------


@router.get("/envs")
async def get_envs(request: Request) -> dict:
    from vectora.services import auth as auth_svc

    user = getattr(request.state, "user", None)
    if user is None:
        raise HTTPException(status_code=401, detail="Não autenticado.")
    overrides = await auth_svc.get_env_overrides(user.id)
    # Mascara valores para exibição — nunca retorna o valor real para o cliente
    masked = {k: "••••••••" for k in overrides}
    return {"envs": masked, "keys": list(overrides.keys())}


@router.post("/envs")
async def set_env(body: EnvOverrideRequest, request: Request) -> dict:
    from vectora.services import auth as auth_svc

    user = getattr(request.state, "user", None)
    if user is None:
        raise HTTPException(status_code=401, detail="Não autenticado.")
    await auth_svc.set_env_override(user.id, body.key, body.value)
    return {"ok": True}


@router.delete("/envs/{key}")
async def delete_env(key: str, request: Request) -> dict:
    from vectora.services import auth as auth_svc

    user = getattr(request.state, "user", None)
    if user is None:
        raise HTTPException(status_code=401, detail="Não autenticado.")
    await auth_svc.delete_env_override(user.id, key)
    return {"ok": True}

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

from src.api.schemas import (
    AuditEntry,
    ChangePasswordRequest,
    EnvOverrideRequest,
    HasUsersResponse,
    InviteValidationResponse,
    RefreshRequest,
    SigninRequest,
    SignoutRequest,
    SignupRequest,
    TokenResponse,
    UpdateProfileRequest,
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
    from src.services.auth import has_users

    return HasUsersResponse(exists=await has_users())


@router.get("/invite/{token}", response_model=InviteValidationResponse)
async def validate_invite_endpoint(token: str) -> InviteValidationResponse:
    """Valida um token de convite para a página de signup pré-verificar."""
    from src.services import auth as auth_svc

    info = await auth_svc.validate_invite(token)
    if info is None:
        return InviteValidationResponse(valid=False)
    return InviteValidationResponse(valid=True, email=info["email"], role=info["role"])


@router.post("/signup", response_model=TokenResponse)
async def signup_endpoint(
    body: SignupRequest,
    request: Request,
    response: Response,
) -> TokenResponse:
    """Cria conta.

    Camadas de autorização:
    1. Sem usuários ainda → signup do root permitido.
    2. Token de convite válido → permitido com a role do convite (consumido).
    3. Caso contrário → 403.

    Retorna tokens via JSON e também os grava em cookies httpOnly.
    """
    from src.services import auth as auth_svc

    invite_role = None
    invite_token = body.invite_token.strip()

    if await auth_svc.has_users():
        invite = await auth_svc.validate_invite(invite_token) if invite_token else None
        if invite is None:
            raise HTTPException(
                status_code=403,
                detail="Signup público desabilitado. Contate o administrador.",
            )
        invite_role = invite["role"]

    try:
        user, access_token, refresh_token = await auth_svc.signup(
            body.email, body.password, role=invite_role, name=body.name
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if invite_token:
        await auth_svc.consume_invite(invite_token, user.id)

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
    from src.services import auth as auth_svc

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
    from src.services import auth as auth_svc

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
    from src.services import auth as auth_svc

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


@router.patch("/me", response_model=UserResponse)
async def update_me_endpoint(
    body: UpdateProfileRequest, request: Request
) -> UserResponse:
    """Atualiza campos do próprio perfil. Atualmente: apenas ``name``."""
    user = getattr(request.state, "user", None)
    if user is None:
        raise HTTPException(status_code=401, detail="Não autenticado.")

    from src.services import auth as auth_svc

    if body.name is not None:
        try:
            updated = await auth_svc.update_profile(user.id, name=body.name)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return UserResponse.from_user(updated)

    return UserResponse.from_user(user)


@router.get("/usage")
async def get_usage(request: Request) -> dict:
    """Consumo de requisições do usuário na janela de rate limit (R5)."""
    user = getattr(request.state, "user", None)
    if user is None:
        raise HTTPException(status_code=401, detail="Não autenticado.")
    from src.services.usage import usage_tracker

    return usage_tracker.usage(user.id)


@router.get("/ws-token")
async def get_ws_token(request: Request) -> dict:
    """Devolve o access token (do cookie) para uso em WebSockets cross-origin.

    O cookie é httpOnly — o JS do browser não consegue lê-lo. Para conectar ao
    WebSocket do terminal, expomos o token via JSON para que o front passe na
    query string da conexão (cookies não trafegam em WS cross-origin).
    """
    user = getattr(request.state, "user", None)
    if user is None:
        raise HTTPException(status_code=401, detail="Não autenticado.")
    token = request.cookies.get(_ACCESS_COOKIE, "")
    if not token:
        # Sem cookie: pode ter vindo via Bearer header — devolve o que veio.
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Sem token disponível.")
    return {"token": token}


@router.post("/change-password")
async def change_password_endpoint(
    body: ChangePasswordRequest,
    request: Request,
    response: Response,
) -> dict:
    from src.services import auth as auth_svc

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
    from src.services.auth import get_db_for_audit
    from src.services.permissions import require_min_role

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
    from src.services.auth import get_db_for_audit
    from src.services.permissions import require_min_role

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

    from src.services.auth import get_db_for_audit
    from src.services.permissions import require_min_role

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
    from src.services import auth as auth_svc

    user = getattr(request.state, "user", None)
    if user is None:
        raise HTTPException(status_code=401, detail="Não autenticado.")
    overrides = await auth_svc.get_env_overrides(user.id)
    # Mascara valores para exibição — nunca retorna o valor real para o cliente
    masked = dict.fromkeys(overrides, "••••••••")
    return {"envs": masked, "keys": list(overrides.keys())}


@router.post("/envs")
async def set_env(body: EnvOverrideRequest, request: Request) -> dict:
    from src.services import auth as auth_svc

    user = getattr(request.state, "user", None)
    if user is None:
        raise HTTPException(status_code=401, detail="Não autenticado.")
    await auth_svc.set_env_override(user.id, body.key, body.value)
    return {"ok": True}


@router.delete("/envs/{key}")
async def delete_env(key: str, request: Request) -> dict:
    from src.services import auth as auth_svc

    user = getattr(request.state, "user", None)
    if user is None:
        raise HTTPException(status_code=401, detail="Não autenticado.")
    await auth_svc.delete_env_override(user.id, key)
    return {"ok": True}

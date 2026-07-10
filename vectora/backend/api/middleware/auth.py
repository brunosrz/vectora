"""Middleware de autenticação para a API FastAPI do Vectora.

Injeta `request.state.user` (User | None) em cada request.
Retorna 401 se o endpoint requer auth e o token está ausente/inválido.

Rotas EXCLUÍDAS da autenticação obrigatória:
- /health, /docs, /openapi.json
- /auth/*  (signup, signin, refresh, signout, has-users)
- arquivos estáticos (extensão de arquivo presente na path)
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

logger = logging.getLogger(__name__)

# Prefixos de rota que NUNCA exigem autenticação
_PUBLIC_PREFIXES: tuple[str, ...] = (
    "/auth/",
    "/health",
    "/license/",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/favicon",
)

# Prefixos exclusivos da API Vectora.
# Rotas que NÃO batem com nenhum desses prefixos são tratadas como
# rotas do frontend (SPA / proxy dev) e portanto são públicas.
# O TanStack Router na SPA cuida da autenticação via beforeLoad.
_API_PREFIXES: tuple[str, ...] = (
    "/auth/",
    "/admin",
    "/memory",
    "/plugins",
    "/tools",
    "/vectora.",
    "/oauth",
    "/health",
    "/license",
    "/metrics",
    "/workspaces",
    "/skills",
    "/artifacts",
    "/threads",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/favicon",
)

# Rotas de API que são publicamente acessíveis (sem token).
# Sobrepõe _API_PREFIXES: um path que bate aqui é público mesmo sendo API.
_EXTRA_PUBLIC_PREFIXES: tuple[str, ...] = (
    "/threads/share/",  # viewer público de conversas compartilhadas
    "/settings/flags",  # feature flags — frontend precisa antes do login
)

# VECTORA_AUTH_REQUIRED=false desabilita auth (modo dev local / CLI)
import os as _os


def _auth_enabled() -> bool:
    """Lê VECTORA_AUTH_REQUIRED em tempo de request (não em import-time).

    Isso permite que testes unitários definam a variável antes de criar o app.
    """
    return _os.getenv("VECTORA_AUTH_REQUIRED", "true").lower() not in {
        "false",
        "0",
        "no",
    }


def _is_public_route(path: str) -> bool:
    """True se a rota é pública (não requer token).

    Lógica em camadas:
    1. Se a rota não bate com nenhum prefixo de API, é uma rota do frontend
       (SPA / proxy dev) → pública; o TanStack Router cuida da auth no browser.
    2. Prefixos de API explicitamente públicos (_EXTRA_PUBLIC_PREFIXES).
    3. Arquivos estáticos (extensão na última parte do path) → públicos.
    4. Prefixos explicitamente públicos da API (_PUBLIC_PREFIXES).
    """
    # Rotas fora da API → frontend → pública
    if not any(path.startswith(p) for p in _API_PREFIXES):
        return True
    # Rotas de API marcadas explicitamente como públicas (ex.: viewer de share)
    if any(path.startswith(p) for p in _EXTRA_PUBLIC_PREFIXES):
        return True
    # Arquivos estáticos (extensão presente) são sempre públicos
    last_segment = path.rsplit("/", maxsplit=1)[-1]
    if "." in last_segment:
        return True
    return any(path.startswith(p) for p in _PUBLIC_PREFIXES)


async def _extract_user(request: Request) -> Any:
    """Tenta extrair e validar o usuário do token JWT.

    Aceita:
    1. Header ``Authorization: Bearer <token>``
    2. Cookie ``vectora_access``

    Retorna User ou None.
    """
    from jwt import PyJWTError as JWTError

    from backend.rbac.auth import decode_access_token, get_user_by_id

    token: str | None = None

    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
    elif "vectora_access" in request.cookies:
        token = request.cookies["vectora_access"]

    user: Any = None
    if token:
        try:
            payload = decode_access_token(token)
            user_id: str = payload.get("sub", "")
            if user_id:
                # Expõe o `exp` (epoch seconds) do access token via
                # request.state para que /auth/me possa devolvê-lo ao
                # frontend — o cookie é httpOnly (JS não enxerga o JWT
                # bruto), então sem isso o cliente não sabe quando renovar.
                request.state.token_exp = payload.get("exp")
                user = await get_user_by_id(user_id)
        except JWTError:
            user = None
        except Exception as exc:
            logger.debug("auth middleware: erro ao validar token: %s", exc)
            user = None

    if user is None and not _auth_enabled():
        return _get_virtual_local_user()
    return user


def _get_virtual_local_user() -> Any:
    """Retorna um objeto User virtual representando o usuário local gratuito."""
    from datetime import UTC, datetime

    from backend.rbac.auth import User
    from backend.rbac.username import slugify_username
    from backend.services.local_user import read_local_user
    from backend.settings import settings as settings_singleton

    name = (
        read_local_user()["name"]
        or settings_singleton.local_user_name
        or "Local User"
    )
    return User(
        id="local",
        username=slugify_username(name),
        email="",
        role="root",
        name=name,
        env_overrides={},
        created_at=datetime.now(UTC).isoformat(),
    )


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware que injeta request.state.user e protege rotas privadas."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        path = request.url.path

        if not _auth_enabled() or _is_public_route(path):
            # Rotas públicas não bloqueiam, mas tentamos extrair o usuário
            # para que handlers como /auth/me possam verificar autenticação.
            request.state.user = await _extract_user(request)
            return await call_next(request)

        user = await _extract_user(request)
        request.state.user = user

        # Rotas privadas exigem usuário autenticado
        if user is None:
            from fastapi.responses import JSONResponse

            return JSONResponse(
                {"detail": "Não autenticado. Forneça um Bearer token válido."},
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )

        return await call_next(request)

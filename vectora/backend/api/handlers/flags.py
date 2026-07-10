"""Endpoint público de feature flags.

F1 — GET /settings/flags → retorna flags de feature para o frontend.
Rota pública (sem autenticação) — o frontend precisa saber as flags
antes do login para renderizar a UI corretamente.

``auth_required`` reflete a mesma leitura de ``VECTORA_AUTH_REQUIRED`` que o
``AuthMiddleware`` usa pra decidir se bloqueia rotas privadas — o guard de
rota do frontend (`__root.tsx`) lê daqui pra saber se pula o fluxo de
login/signup (modo local, sem conta) sem precisar de rebuild.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from backend.api.middleware.auth import _auth_enabled
from backend.settings import get_settings

router = APIRouter(prefix="/settings", tags=["flags"])


@router.get("/flags")
async def get_flags() -> dict:
    settings = get_settings()
    return {
        "enable_features_beta": settings.enable_features_beta,
        "auth_required": _auth_enabled(),
    }


def _user_id_from_request(request: Request) -> str:
    user = getattr(request.state, "user", None)
    return getattr(user, "id", None) or "local"


@router.get("/prefs")
async def get_prefs(request: Request) -> dict:
    """Preferências durável do frontend (modelo selecionado, tema, etc.).

    Fonte de verdade no backend (CLAUDE.md §8) — sobrevive a reinstalar o app
    ou limpar o cache do navegador, diferente do que fica só no localStorage.
    """
    from backend.workspace.runtime_settings import runtime_settings

    return runtime_settings.get_frontend_prefs(_user_id_from_request(request))


@router.patch("/prefs")
async def update_prefs(request: Request) -> dict:
    """Mescla preferências enviadas pelo frontend e devolve o estado final.

    Campos não reconhecidos são ignorados (ver
    ``runtime_settings._ALLOWED_FRONTEND_PREF_KEYS``) — forward-compat com um
    frontend mais novo que o backend.
    """
    from backend.workspace.runtime_settings import runtime_settings

    body = await request.json()
    if not isinstance(body, dict):
        raise HTTPException(status_code=422, detail="Corpo deve ser um objeto JSON.")
    return runtime_settings.set_frontend_prefs(_user_id_from_request(request), body)

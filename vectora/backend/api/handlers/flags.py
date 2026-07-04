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

from fastapi import APIRouter

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

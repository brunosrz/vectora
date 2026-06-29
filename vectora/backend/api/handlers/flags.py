"""Endpoint público de feature flags.

F1 — GET /settings/flags → retorna flags de feature para o frontend.
Rota pública (sem autenticação) — o frontend precisa saber as flags
antes do login para renderizar a UI corretamente.
"""

from __future__ import annotations

from fastapi import APIRouter

from backend.settings import get_settings

router = APIRouter(prefix="/settings", tags=["flags"])


@router.get("/flags")
async def get_flags() -> dict:
    settings = get_settings()
    return {"enable_features_beta": settings.enable_features_beta}

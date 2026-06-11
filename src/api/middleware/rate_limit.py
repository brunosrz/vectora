"""Rate limiting para endpoints sensíveis do Vectora.

Usa slowapi (wrapper de limits sobre FastAPI).

Limites por endpoint:
    POST /auth/signin         → 5 req/min por IP (failure-based logic via auth service)
    POST /auth/signup         → 3 req/hora por IP
    POST /auth/change-password → 3 req/hora por user_id
    POST /auth/refresh        → 20 req/min por IP

Os outros endpoints (StreamChat, etc.) não têm rate limit aqui —
são protegidos pela autenticação obrigatória.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request

logger = logging.getLogger(__name__)


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def attach_limiter(app: FastAPI) -> None:
    """Configura slowapi no app FastAPI e aplica limites globais."""
    try:
        from slowapi import Limiter, _rate_limit_exceeded_handler
        from slowapi.errors import RateLimitExceeded
        from slowapi.util import get_remote_address

        # Bloco G — storage distribuído: com REDIS_URL os contadores vivem no
        # Redis e valem para todas as réplicas; sem ele, memória local.
        from src.settings import settings

        storage_uri = (settings.redis_url or "").strip() or "memory://"
        limiter = Limiter(key_func=get_remote_address, storage_uri=storage_uri)
        app.state.limiter = limiter
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]

        # Decoramos os endpoints via state — os handlers usam app.state.limiter
        logger.info(
            "rate_limit: slowapi configurado (storage=%s)",
            "redis" if storage_uri.startswith("redis") else "memory",
        )
    except Exception as exc:
        logger.warning("rate_limit: slowapi não disponível: %s", exc)


def get_limiter(request: Request) -> Any:
    """Retorna o limiter do state do app (helper para handlers)."""
    return getattr(request.app.state, "limiter", None)

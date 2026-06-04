"""Handler de status e portal de licença.

Endpoints:

- ``GET /license/status`` — público, lê cache local que o Launcher escreveu
  no boot. Consumido pelo trial banner do chat.
- ``POST /license/portal`` — autenticado, chama a edge function Supabase
  ``create-portal`` (Stripe Customer Portal para INTL ou Asaas dashboard
  para BR) e retorna a URL pra abrir externamente.

Roteamento BR vs INTL fica na edge function — o backend só repassa o token.
"""

from __future__ import annotations

import logging
import os

import httpx
from fastapi import APIRouter, HTTPException, Request

from src.services.license import LicenseError, read_cached_status

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/license", tags=["license"])

DEFAULT_PORTAL_URL = "https://vectora.company/functions/v1/create-portal"
HTTP_TIMEOUT = 10.0


@router.get("/status")
async def license_status() -> dict:
    """Devolve o status atual da licença (lido do cache local)."""
    info = read_cached_status()
    if info is None:
        return {
            "configured": False,
            "tier": None,
            "status": "unknown",
            "days_remaining": 0,
            "expires_at": "",
            "cached": False,
        }
    return {"configured": True, **info.to_dict()}


def _portal_url() -> str:
    return os.getenv("VECTORA_LICENSE_PORTAL_URL", DEFAULT_PORTAL_URL).strip()


def _vectora_token() -> str:
    token = os.getenv("VECTORA_TOKEN", "").strip()
    if not token:
        raise LicenseError(
            "VECTORA_TOKEN não configurado — não há licença para gerenciar."
        )
    return token


@router.post("/portal")
async def license_portal(request: Request) -> dict:
    """Cria sessão de Customer Portal (Stripe INTL ou Asaas BR).

    Repassa o ``VECTORA_TOKEN`` para a edge function `create-portal` que
    decide o provedor pelo país do usuário (`profiles.country`). Retorna
    ``{url: str}`` para o desktop abrir via ``shell.openExternal()`` ou o
    web abrir em nova aba.
    """
    try:
        token = _vectora_token()
    except LicenseError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    payload = {"token": token}
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            resp = await client.post(_portal_url(), json=payload)
    except httpx.HTTPError as exc:
        logger.warning("license/portal: falha de network — %s", exc)
        raise HTTPException(
            status_code=503,
            detail="Servidor de billing indisponível. Tente novamente em instantes.",
        ) from exc

    if resp.status_code == 401:
        raise HTTPException(status_code=401, detail="Token inválido.")
    if resp.status_code == 404:
        raise HTTPException(
            status_code=404,
            detail="Sem assinatura ativa para gerenciar.",
        )
    if resp.status_code >= 500:
        raise HTTPException(
            status_code=502,
            detail="Erro no servidor de billing.",
        )
    if resp.status_code >= 400:
        # Repassa mensagem da edge function quando disponível.
        detail = "Erro ao criar sessão de portal."
        try:
            detail = resp.json().get("message", detail)
        except Exception:
            pass
        raise HTTPException(status_code=resp.status_code, detail=detail)

    data = resp.json()
    url = data.get("url", "").strip()
    if not url:
        raise HTTPException(
            status_code=502,
            detail="Resposta inválida do servidor de billing.",
        )
    return {"url": url}

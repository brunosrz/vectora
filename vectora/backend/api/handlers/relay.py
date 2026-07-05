"""Endpoints de gerenciamento do relay local.

R1 — GET  /relay/status  → estado atual da conexão (token, subdomain, connected)
R2 — POST /relay/revoke  → revoga o token no Worker e limpa ~/.vectora/relay_token
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import aiohttp
from fastapi import APIRouter, HTTPException, Request

from backend.services.relay.token import load_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/relay", tags=["relay"])

_TOKEN_PATH = Path.home() / ".vectora" / "relay_token"
_RELAY_BASE = os.environ.get("RELAY_URL", "https://relay.vectora.chat")


def _require_auth(request: Request) -> None:
    if getattr(request.state, "user", None) is None:
        raise HTTPException(status_code=401, detail="Não autenticado")


def _relay_token() -> str | None:
    return load_token(_TOKEN_PATH)


def _subdomain(token: str) -> str:
    return f"{token}.vectora.chat"


@router.get("/status")
async def relay_status(request: Request) -> dict:
    _require_auth(request)
    token = _relay_token()
    if not token:
        return {
            "connected": False,
            "token": None,  # nosec B105
            "subdomain": None,
            "webhook_base": None,
        }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{_RELAY_BASE}/health/{token}", timeout=aiohttp.ClientTimeout(total=3)
            ) as resp:
                data = await resp.json() if resp.status == 200 else {}
                connected = bool(data.get("connected", False))
    except Exception:
        connected = False

    sub = _subdomain(token)
    return {
        "connected": connected,
        "token": token,
        "subdomain": sub,
        "webhook_base": f"https://{sub}",
    }


@router.post("/revoke")
async def relay_revoke(request: Request) -> dict:
    _require_auth(request)
    token = _relay_token()
    if not token:
        raise HTTPException(status_code=404, detail="Nenhum token de relay ativo")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.delete(
                f"{_RELAY_BASE}/relay/session/{token}",
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                if resp.status not in (200, 404):
                    logger.warning(
                        "relay: revoke retornou %d para token %s", resp.status, token
                    )
    except Exception as exc:
        logger.warning("relay: falha ao revogar token no Worker — %s", exc)

    _TOKEN_PATH.unlink(missing_ok=True)
    logger.info("relay: token %s revogado e removido de %s", token, _TOKEN_PATH)
    return {"revoked": True}

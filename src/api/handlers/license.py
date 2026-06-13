"""Handler de status, validação, conexão e portal de licença.

Endpoints:

- ``GET /license/status`` — público, lê cache local que o Launcher escreveu
  no boot. Consumido pelo trial banner do chat.
- ``POST /license/validate`` — força revalidação remota do token atual e
  devolve o status fresco. Usado pelo setup wizard após salvar token.
- ``POST /license/connect`` — root only. Login com a conta vectora.company
  (email + senha): a edge function ``agent-login`` autentica e devolve um
  VECTORA_TOKEN, que é persistido e validado — conecta tudo em um passo.
- ``POST /license/portal`` — autenticado, chama a edge function Supabase
  ``create-portal`` (Stripe Customer Portal para INTL ou Asaas dashboard
  para BR) e retorna a URL pra abrir externamente.

Roteamento BR vs INTL fica na edge function — o backend só repassa o token.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from src.services.license import (
    LicenseError,
    clear_license_cache,
    read_cached_status,
    validate_license_async,
    write_token_to_config,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/license", tags=["license"])

DEFAULT_PORTAL_URL = "https://vectora.company/functions/v1/create-portal"
DEFAULT_CONNECT_URL = "https://vectora.company/functions/v1/agent-login"
HTTP_TIMEOUT = 10.0


def _require_root(request: Request) -> Any:
    """Lança 401/403 se o usuário da request não é root (espelha admin.py)."""
    user = getattr(request.state, "user", None)
    if user is None:
        raise HTTPException(status_code=401, detail="Não autenticado.")
    if getattr(user, "role", None) != "root":
        raise HTTPException(
            status_code=403,
            detail="Acesso negado. Apenas root pode configurar a licença.",
        )
    return user


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


@router.post("/validate")
async def license_validate() -> dict:
    """Força revalidação remota do token atual (ignora cache fresco).

    Sempre responde 200; falha de licença vai em ``{valid: false, error}``
    para o wizard exibir inline sem tratar status HTTP.
    """
    if not os.getenv("VECTORA_TOKEN", "").strip():
        # _get_token() em license.py também lê do config.toml — deixa o
        # serviço decidir; aqui só damos resposta amigável se nada existir.
        from src.services.license import load_token_from_config

        if not load_token_from_config():
            return {"valid": False, "configured": False, "error": "token_missing"}
    try:
        info = await validate_license_async(force=True)
    except LicenseError as exc:
        return {"valid": False, "configured": True, "error": str(exc)}
    except Exception as exc:  # network/5xx — não derruba o wizard
        logger.warning("license/validate: falha inesperada — %s", exc)
        return {"valid": False, "configured": True, "error": "Falha ao validar."}
    return {"valid": True, "configured": True, **info.to_dict()}


class ConnectBody(BaseModel):
    """Credenciais da conta vectora.company para conectar a licença."""

    email: str
    password: str


def _connect_url() -> str:
    return os.getenv("VECTORA_LICENSE_CONNECT_URL", DEFAULT_CONNECT_URL).strip()


@router.post("/connect")
async def license_connect(body: ConnectBody, request: Request) -> dict:
    """Login com a conta vectora.company → obtém e ativa o VECTORA_TOKEN.

    Chama a edge function ``agent-login`` (email + senha). Em caso de sucesso
    ela devolve ``{token, tier, status}``; o token é persistido em
    ``config.toml [license]`` e validado imediatamente (popula o cache que o
    banner e o /license/status leem).
    """
    _require_root(request)
    email = body.email.strip()
    if "@" not in email or not body.password:
        raise HTTPException(status_code=422, detail="Credenciais incompletas.")

    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            resp = await client.post(
                _connect_url(),
                json={"email": email, "password": body.password},
            )
    except httpx.HTTPError as exc:
        logger.warning("license/connect: falha de network — %s", exc)
        raise HTTPException(
            status_code=503,
            detail="vectora.company indisponível. Tente novamente em instantes.",
        ) from exc

    if resp.status_code == 401:
        raise HTTPException(status_code=401, detail="Email ou senha incorretos.")
    if resp.status_code == 404:
        raise HTTPException(
            status_code=404,
            detail="Conta sem token de licença. Acesse o dashboard para gerar um.",
        )
    if resp.status_code >= 400:
        logger.warning("license/connect: edge function respondeu %s", resp.status_code)
        raise HTTPException(status_code=502, detail="Erro no servidor de licenças.")

    data = resp.json()
    token = str(data.get("token", "")).strip()
    if not token:
        raise HTTPException(
            status_code=502, detail="Resposta inválida do servidor de licenças."
        )

    # Persiste e ativa o token novo; o cache antigo é descartado para a
    # validação refletir a conta recém-conectada.
    os.environ["VECTORA_TOKEN"] = token
    write_token_to_config(token)
    clear_license_cache()

    try:
        info = await validate_license_async(force=True)
    except LicenseError as exc:
        return {"connected": True, "valid": False, "error": str(exc)}
    return {"connected": True, "valid": True, **info.to_dict()}


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
        import contextlib
        import json

        detail = "Erro ao criar sessão de portal."
        with contextlib.suppress(json.JSONDecodeError, AttributeError, TypeError):
            detail = resp.json().get("message", detail)
        raise HTTPException(status_code=resp.status_code, detail=detail)

    data = resp.json()
    url = data.get("url", "").strip()
    if not url:
        raise HTTPException(
            status_code=502,
            detail="Resposta inválida do servidor de billing.",
        )
    return {"url": url}

"""Tool de requisição HTTP genérica."""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx
from langchain.tools import tool

logger = logging.getLogger(__name__)


@tool
async def http_request(
    url: str,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    body: str | None = None,
    timeout: float = 15.0,
) -> str:
    """Executa uma requisição HTTP e retorna status + body.

    Retorna JSON com ``{"status": int, "body": str}``.

    Args:
        url: URL completa da requisição.
        method: Método HTTP — GET, POST, PUT, PATCH, DELETE.
        headers: Cabeçalhos opcionais.
        body: Corpo da requisição (para POST/PUT).
        timeout: Timeout em segundos (padrão 15).
    """
    try:
        kwargs: dict[str, Any] = {"timeout": timeout}
        if headers:
            kwargs["headers"] = headers
        if body:
            kwargs["content"] = body.encode()
        async with httpx.AsyncClient(**kwargs) as client:
            resp = await client.request(method.upper(), url)
            return json.dumps({"status": resp.status_code, "body": resp.text})
    except httpx.TimeoutException as e:
        return f"error: timeout — {e}"
    except Exception as e:
        logger.exception("http_request falhou", extra={"url": url, "method": method})
        return f"error: {e}"

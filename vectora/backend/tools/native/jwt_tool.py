"""Tool de decodificação de JWT sem verificação de assinatura."""

from __future__ import annotations

import json
import logging

from langchain.tools import tool

logger = logging.getLogger(__name__)


@tool
async def jwt_decode(token: str) -> str:
    """Decodifica o payload de um JWT sem verificar a assinatura.

    Útil para inspecionar claims (sub, exp, roles, etc.) de forma rápida.

    Args:
        token: Token JWT no formato ``header.payload.signature``.
    """
    try:
        import jwt

        payload = jwt.decode(token, options={"verify_signature": False})
        return json.dumps(payload)
    except Exception as e:
        logger.exception("jwt_decode falhou")
        return f"error: {e}"

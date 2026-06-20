"""Tool de encode/decode base64."""

from __future__ import annotations

import base64
import logging

from langchain.tools import tool

logger = logging.getLogger(__name__)


@tool
async def base64_encode(text: str, operation: str = "encode") -> str:
    """Codifica ou decodifica uma string em Base64.

    Args:
        text: String a ser processada.
        operation: "encode" para codificar, "decode" para decodificar.
    """
    try:
        if operation == "encode":
            return base64.b64encode(text.encode()).decode()
        elif operation == "decode":
            return base64.b64decode(text).decode()
        else:
            return f"error: operação inválida: {operation!r}. Use 'encode' ou 'decode'."
    except Exception as e:
        logger.exception("base64_encode falhou", extra={"operation": operation})
        return f"error: {e}"

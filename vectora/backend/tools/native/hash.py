"""Tool de hash criptográfico de strings."""

from __future__ import annotations

import hashlib
import logging

from langchain.tools import tool

logger = logging.getLogger(__name__)

_SUPPORTED = {"md5", "sha256", "sha512"}


@tool
async def hash_text(text: str, algorithm: str = "sha256") -> str:
    """Calcula o hash de uma string usando o algoritmo especificado.

    Args:
        text: Texto a ser hasheado.
        algorithm: Algoritmo a usar — "md5", "sha256" ou "sha512".
    """
    try:
        if algorithm not in _SUPPORTED:
            return f"error: algoritmo não suportado: {algorithm!r}. Use: {sorted(_SUPPORTED)}"
        return hashlib.new(algorithm, text.encode()).hexdigest()
    except Exception as e:
        logger.exception("hash_text falhou", extra={"algorithm": algorithm})
        return f"error: {e}"

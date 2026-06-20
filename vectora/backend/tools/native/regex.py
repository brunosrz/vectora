"""Tool de teste de expressões regulares."""

from __future__ import annotations

import json
import logging
import re

from langchain.tools import tool

logger = logging.getLogger(__name__)


@tool
async def regex_test(pattern: str, text: str) -> str:
    """Testa uma expressão regular sobre um texto e retorna os matches.

    Retorna JSON com ``{"matched": bool, "matches": [str, ...]}``.

    Args:
        pattern: Expressão regular (sintaxe Python ``re``).
        text: Texto alvo.
    """
    try:
        compiled = re.compile(pattern)
        matches = compiled.findall(text)
        return json.dumps({"matched": bool(matches), "matches": matches})
    except re.error as e:
        return f"error: padrão regex inválido: {e}"
    except Exception as e:
        logger.exception("regex_test falhou", extra={"pattern": pattern})
        return f"error: {e}"

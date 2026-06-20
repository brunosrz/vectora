"""Tool de consulta de campos JSON via path pontilhado com suporte a índices."""

from __future__ import annotations

import json
import logging
import re
from typing import Any, cast

from langchain.tools import tool

logger = logging.getLogger(__name__)

_INDEX_RE = re.compile(r"\[(\d+)\]")


def _resolve_path(obj: object, path: str) -> object:
    """Navega ``obj`` seguindo ``path`` no formato ``a.b[0].c``."""
    parts: list[str | int] = []
    for segment in path.split("."):
        head, *rest = _INDEX_RE.split(segment)
        if head:
            parts.append(head)
        for i, r in enumerate(rest):
            if i % 2 == 0:
                parts.append(int(r))
    current: Any = obj
    for part in parts:
        if isinstance(part, int):
            if not isinstance(current, list) or part >= len(current):
                raise KeyError(f"índice [{part}] fora do limite")
            current = cast(list[Any], current)[part]
        elif isinstance(current, dict):
            if part not in current:
                raise KeyError(f"chave ausente: {part!r}")
            current = cast(dict[str, Any], current)[part]
        else:
            raise KeyError(f"não é possível navegar em {type(current).__name__}")
    return current


@tool
async def json_query(json_text: str, path: str) -> str:
    """Extrai um campo de um JSON usando path pontilhado (ex: ``a.b[0].c``).

    Args:
        json_text: String JSON a ser consultada.
        path: Caminho pontilhado com suporte a índices (ex: "users[0].name").
    """
    try:
        obj = json.loads(json_text)
        value = _resolve_path(obj, path)
        return str(value) if not isinstance(value, str) else value
    except json.JSONDecodeError as e:
        return f"error: JSON inválido: {e}"
    except KeyError as e:
        return f"error: {e}"
    except Exception as e:
        logger.exception("json_query falhou", extra={"path": path})
        return f"error: {e}"

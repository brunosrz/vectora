"""Tools de data e hora."""

from __future__ import annotations

import logging
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from langchain.tools import tool

logger = logging.getLogger(__name__)


@tool
async def time_now(timezone: str = "UTC") -> str:
    """Retorna a data/hora atual no fuso horário especificado (padrão: UTC).

    Args:
        timezone: Nome do fuso horário IANA (ex: "America/Sao_Paulo", "UTC").
    """
    try:
        tz = ZoneInfo(timezone)
        return datetime.now(tz).isoformat()
    except ZoneInfoNotFoundError:
        return f"error: fuso horário desconhecido: {timezone!r}"
    except Exception as e:
        logger.exception("time_now falhou", extra={"timezone": timezone})
        return f"error: {e}"


@tool
async def time_parse(text: str) -> str:
    """Converte uma string de data/hora para ISO 8601.

    Aceita formatos ISO e formatos naturais em inglês (ex: "January 15, 2024").

    Args:
        text: String de data/hora a ser interpretada.
    """
    try:
        from dateutil import parser as _p

        dt = _p.parse(text)
        return dt.isoformat()
    except Exception as e:
        logger.exception("time_parse falhou", extra={"text": text})
        return f"error: não foi possível interpretar a data: {e}"

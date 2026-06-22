"""Tool: parse datetime from string."""

from datetime import datetime

from dateutil import parser
from langchain.tools import tool


@tool
async def time_parse(date_string: str, format_hint: str = "iso") -> str:
    """Parse string para datetime (ISO ou human-readable).

    Args:
        date_string: String de data (ex: "2024-06-21" ou "next Monday")
        format_hint: "iso" ou "human"

    Returns:
        ISO datetime string ou erro
    """
    try:
        dt = parser.parse(date_string)
        return dt.isoformat()
    except Exception as e:
        return f"error: não consegui fazer parse de '{date_string}' — {e}"

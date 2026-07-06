"""Automação de browser do agente sobre o preview do workspace (Playwright).

Escopo deliberadamente restrito: só navega dentro do dev server que o
próprio workspace já tem rodando (ver `resolve_preview_url`) — nunca URLs
livres da internet (isso é papel do `fetch_url`/`web_search`).
"""

from __future__ import annotations

from backend.browser.preview import resolve_preview_url
from backend.browser.session import close_all_browser_sessions, get_browser_page

__all__ = ["close_all_browser_sessions", "get_browser_page", "resolve_preview_url"]

"""Sessão de browser headless (Playwright) persistente por workspace.

Uma aba (`Page`) sobrevive entre chamadas de tool dentro do mesmo
workspace — clicar/preencher/rolar constroem em cima da navegação
anterior, em vez de reabrir a página do zero a cada tool call.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_sessions: dict[str, dict[str, Any]] = {}


def has_browser_session(workspace_id: str) -> bool:
    """True se já existe uma sessão (browser lançado) pra esse workspace —
    sem criar uma nova. Usado pra evitar lançar Chromium à toa quando nem
    há dev server nem uma navegação prévia (`browser_navigate`)."""
    return workspace_id in _sessions


async def get_browser_page(workspace_id: str) -> Any:
    """Retorna a `Page` ativa do workspace, criando o browser sob demanda."""
    session = _sessions.get(workspace_id)
    if session is not None:
        return session["page"]

    from playwright.async_api import async_playwright

    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=True)
    page = await browser.new_page(viewport={"width": 1280, "height": 800})
    _sessions[workspace_id] = {
        "playwright": playwright,
        "browser": browser,
        "page": page,
    }
    logger.info("browser_session_started", extra={"workspace_id": workspace_id})
    return page


async def close_browser_session(workspace_id: str) -> None:
    """Fecha e descarta a sessão de browser de um workspace, se existir."""
    session = _sessions.pop(workspace_id, None)
    if session is None:
        return
    try:
        await session["browser"].close()
        await session["playwright"].stop()
    except Exception:
        logger.exception(
            "browser_session_close_failed", extra={"workspace_id": workspace_id}
        )


async def close_all_browser_sessions() -> None:
    """Fecha todas as sessões de browser abertas (shutdown do backend)."""
    for workspace_id in list(_sessions):
        await close_browser_session(workspace_id)

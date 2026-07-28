"""Sessão de browser headless (Playwright) persistente por workspace.

Uma aba (`Page`) sobrevive entre chamadas de tool dentro do mesmo
workspace — clicar/preencher/rolar constroem em cima da navegação
anterior, em vez de reabrir a página do zero a cada tool call.

Workspaces com `[sandbox]` habilitado (`vectora.toml`) ganham um perfil de
browser isolado (`launch_persistent_context` num diretório próprio, nunca
o perfil efêmero padrão nem o de outro workspace) — evita que automação de
browser dentro do jail acumule cookies/sessões que vazem entre workspaces.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_sessions: dict[str, dict[str, Any]] = {}


def has_browser_session(workspace_id: str) -> bool:
    """True se já existe uma sessão (browser lançado) pra esse workspace —
    sem criar uma nova. Usado pra evitar lançar Chromium à toa quando nem
    há dev server nem uma navegação prévia (`browser_navigate`)."""
    return workspace_id in _sessions


def _jailed_profile_dir(workspace_id: str) -> Path | None:
    """Diretório de perfil Playwright isolado pra workspaces sandboxed.

    `None` (perfil efêmero em memória, comportamento atual) pra workspaces
    sem `[sandbox]` habilitado ou qualquer erro ao resolver a política —
    nunca lança exceção, defensivo como o resto do módulo de sandbox."""
    if not workspace_id:
        return None
    try:
        from backend.sandbox.policy import parse_policy
        from backend.workspace.workspace import workspace_registry

        ws = workspace_registry.get(workspace_id)
        cwd = getattr(ws, "cwd", None)
        if not cwd:
            return None
        base = Path(cwd)
        if not parse_policy(base / "vectora.toml").enabled:
            return None
        profile_dir = base / ".vectora" / "sandbox" / "browser-profile" / workspace_id
        profile_dir.mkdir(parents=True, exist_ok=True)
        return profile_dir
    except Exception:
        logger.debug(
            "browser_session: falha ao resolver perfil jailado de %s", workspace_id
        )
        return None


async def get_browser_page(workspace_id: str) -> Any:
    """Retorna a `Page` ativa do workspace, criando o browser sob demanda."""
    session = _sessions.get(workspace_id)
    if session is not None:
        return session["page"]

    from playwright.async_api import async_playwright

    playwright = await async_playwright().start()
    profile_dir = _jailed_profile_dir(workspace_id)
    if profile_dir is not None:
        context = await playwright.chromium.launch_persistent_context(
            str(profile_dir), headless=True, viewport={"width": 1280, "height": 800}
        )
        page = context.pages[0] if context.pages else await context.new_page()
        _sessions[workspace_id] = {
            "playwright": playwright,
            "browser": context,
            "page": page,
        }
        logger.info(
            "browser_session_started_jailed", extra={"workspace_id": workspace_id}
        )
        return page

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

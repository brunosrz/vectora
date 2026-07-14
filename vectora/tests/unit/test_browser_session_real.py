"""Sessão de browser (Playwright/Chromium) contra o processo real — skip
limpo sem o Chromium instalado (`playwright install chromium`).

Diferente de test_tools_browser.py, que mocka Playwright deliberadamente
(ver seu próprio docstring), este arquivo sobe um Chromium headless de
verdade e valida o ciclo de vida completo de `backend/browser/session.py`.
"""

from __future__ import annotations

import pytest

from backend.browser import session as browser_session


def _chromium_available() -> bool:
    from pathlib import Path

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return False

    try:
        with sync_playwright() as p:
            return Path(p.chromium.executable_path).is_file()
    except Exception:
        return False


pytestmark = [
    pytest.mark.browser,
    pytest.mark.skipif(
        not _chromium_available(),
        reason="Chromium não instalado — rode `playwright install chromium`",
    ),
]


@pytest.fixture(autouse=True)
async def _clean_sessions():
    """Garante nenhuma sessão de browser sobrando de um teste anterior."""
    await browser_session.close_all_browser_sessions()
    yield
    await browser_session.close_all_browser_sessions()


@pytest.mark.asyncio
async def test_get_browser_page_sobe_chromium_real_e_navega():
    page = await browser_session.get_browser_page("ws-real-1")
    await page.goto("about:blank")

    assert page.url == "about:blank"

    # Par de erro no mesmo teste: mesmo workspace_id reaproveita a MESMA
    # Page (contrato documentado no docstring do módulo) — não abre um
    # segundo Chromium por chamada.
    page_again = await browser_session.get_browser_page("ws-real-1")
    assert page_again is page


@pytest.mark.asyncio
async def test_close_browser_session_encerra_processo_real_e_recria_ao_reabrir():
    first_page = await browser_session.get_browser_page("ws-real-2")
    await first_page.goto("about:blank")

    await browser_session.close_browser_session("ws-real-2")

    second_page = await browser_session.get_browser_page("ws-real-2")
    assert second_page is not first_page
    await second_page.goto("about:blank")
    assert second_page.url == "about:blank"


@pytest.mark.asyncio
async def test_close_all_browser_sessions_fecha_multiplos_workspaces_reais():
    for ws_id in ("ws-multi-a", "ws-multi-b", "ws-multi-c"):
        page = await browser_session.get_browser_page(ws_id)
        await page.goto("about:blank")

    await browser_session.close_all_browser_sessions()

    assert browser_session._sessions == {}


@pytest.mark.asyncio
async def test_close_browser_session_workspace_inexistente_e_noop():
    # Nenhuma sessão aberta pra esse workspace — não deve lançar.
    await browser_session.close_browser_session("workspace-que-nunca-existiu")

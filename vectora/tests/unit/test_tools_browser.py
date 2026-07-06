"""Tools de browser automation (A2): screenshot/click/scroll/fill/read_dom.

Restrição de escopo (guardrail deliberado): as tools só navegam pra dentro
do dev server que o próprio workspace já subiu (via `.vectora/launch.json`
+ `preview_start`) — nunca uma URL livre da internet. Playwright é mockado
nestes testes (não depende de Chromium instalado).
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from langchain_core.runnables import RunnableConfig

from backend.tools import browser as browser_tools


def _config(workspace_id: str = "ws1") -> RunnableConfig:
    return RunnableConfig(configurable={"workspace_id": workspace_id})


class _FakePage:
    def __init__(self) -> None:
        self.url = "about:blank"
        self.goto = AsyncMock(side_effect=self._goto)
        self.screenshot = AsyncMock(return_value=b"fake-png-bytes")
        self.click = AsyncMock()
        self.fill = AsyncMock()
        self.inner_text = AsyncMock(return_value="Olá mundo")
        self.mouse = AsyncMock()
        self.mouse.wheel = AsyncMock()

    async def _goto(self, url: str, **_kwargs: object) -> None:
        self.url = url


@pytest.fixture
def fake_page(monkeypatch):
    page = _FakePage()
    monkeypatch.setattr(browser_tools, "get_browser_page", AsyncMock(return_value=page))
    return page


@pytest.mark.asyncio
async def test_browser_screenshot_returns_data_url_when_preview_running(
    monkeypatch, fake_page
):
    """Preview ativo → screenshot navega pra URL do preview e devolve data URL base64."""
    monkeypatch.setattr(
        browser_tools,
        "resolve_preview_url",
        AsyncMock(return_value="http://localhost:5173"),
    )

    result = await browser_tools.browser_screenshot.ainvoke({}, config=_config())

    assert result.startswith("data:image/png;base64,")
    fake_page.goto.assert_awaited_once_with(
        "http://localhost:5173", wait_until="domcontentloaded"
    )


@pytest.mark.asyncio
async def test_browser_screenshot_returns_error_when_no_preview_running(monkeypatch):
    """Sem preview rodando no workspace, a tool recusa (não navega pra internet livre)."""
    monkeypatch.setattr(
        browser_tools, "resolve_preview_url", AsyncMock(return_value=None)
    )

    result = await browser_tools.browser_screenshot.ainvoke({}, config=_config())

    assert result.startswith("Error:")
    assert "preview" in result.lower()


@pytest.mark.asyncio
async def test_browser_click_success_and_selector_not_found(monkeypatch, fake_page):
    """Clique bem-sucedido confirma o seletor; seletor inexistente devolve erro claro."""
    monkeypatch.setattr(
        browser_tools,
        "resolve_preview_url",
        AsyncMock(return_value="http://localhost:5173"),
    )

    ok = await browser_tools.browser_click.ainvoke(
        {"selector": "#submit"}, config=_config()
    )
    assert "OK" in ok
    assert "#submit" in ok

    fake_page.click.side_effect = TimeoutError("not found")
    err = await browser_tools.browser_click.ainvoke(
        {"selector": "#ghost"}, config=_config()
    )
    assert err.startswith("Error:")
    assert "#ghost" in err


@pytest.mark.asyncio
async def test_browser_fill_writes_value_and_rejects_missing_field(
    monkeypatch, fake_page
):
    monkeypatch.setattr(
        browser_tools,
        "resolve_preview_url",
        AsyncMock(return_value="http://localhost:5173"),
    )

    ok = await browser_tools.browser_fill.ainvoke(
        {"selector": "input[name=email]", "value": "a@b.com"}, config=_config()
    )
    assert "OK" in ok
    fake_page.fill.assert_awaited_once_with(
        "input[name=email]", "a@b.com", timeout=5000
    )

    fake_page.fill.side_effect = TimeoutError("missing")
    err = await browser_tools.browser_fill.ainvoke(
        {"selector": "#missing", "value": "x"}, config=_config()
    )
    assert err.startswith("Error:")


@pytest.mark.asyncio
async def test_browser_read_dom_returns_text_and_empty_on_missing_selector(
    monkeypatch, fake_page
):
    monkeypatch.setattr(
        browser_tools,
        "resolve_preview_url",
        AsyncMock(return_value="http://localhost:5173"),
    )

    text = await browser_tools.browser_read_dom.ainvoke({}, config=_config())
    assert text == "Olá mundo"

    fake_page.inner_text.side_effect = TimeoutError("missing")
    err = await browser_tools.browser_read_dom.ainvoke(
        {"selector": "#nao-existe"}, config=_config()
    )
    assert err.startswith("Error:")
    assert "#nao-existe" in err


@pytest.mark.asyncio
async def test_browser_scroll_accepts_down_up_and_rejects_invalid_direction(
    monkeypatch, fake_page
):
    monkeypatch.setattr(
        browser_tools,
        "resolve_preview_url",
        AsyncMock(return_value="http://localhost:5173"),
    )

    ok = await browser_tools.browser_scroll.ainvoke(
        {"direction": "down"}, config=_config()
    )
    assert "OK" in ok

    err = await browser_tools.browser_scroll.ainvoke(
        {"direction": "sideways"}, config=_config()
    )
    assert err.startswith("Error:")

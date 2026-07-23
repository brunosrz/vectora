"""Tools de browser: navegação livre (`browser_navigate`) + automação
(screenshot/click/scroll/fill/read_dom) + gestão de dev server.

`browser_navigate` aceita qualquer URL http(s) — único guardrail é o
esquema. As demais tools de automação operam sobre a página já navegada
(sessão persistente); sem nada navegado ainda, caem no dev server ativo do
workspace (`.vectora/launch.json` + `browser_start`). Playwright é mockado
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
async def test_browser_navigate_navega_para_url_http(monkeypatch, fake_page):
    """URL http/https é aceita e navega a página persistente do workspace."""
    result = await browser_tools.browser_navigate.ainvoke(
        {"url": "https://example.com"}, config=_config()
    )

    assert result.startswith("[OK]")
    assert "https://example.com" in result
    fake_page.goto.assert_awaited_once_with(
        "https://example.com", wait_until="domcontentloaded", timeout=15000
    )


@pytest.mark.asyncio
async def test_browser_navigate_recusa_esquema_nao_http(monkeypatch, fake_page):
    """Erro/borda: file:// e outros esquemas não http(s) são recusados antes
    de qualquer tentativa de navegação."""
    result = await browser_tools.browser_navigate.ainvoke(
        {"url": "file:///etc/passwd"}, config=_config()
    )

    assert result.startswith("Error:")
    assert "esquema" in result.lower()
    fake_page.goto.assert_not_called()


@pytest.mark.asyncio
async def test_browser_navigate_javascript_scheme_recusado(monkeypatch, fake_page):
    """Erro/borda: `javascript:` (injeção via URL) também é recusado."""
    result = await browser_tools.browser_navigate.ainvoke(
        {"url": "javascript:alert(1)"}, config=_config()
    )

    assert result.startswith("Error:")
    fake_page.goto.assert_not_called()


@pytest.mark.asyncio
async def test_browser_navigate_falha_de_rede_devolve_erro_claro(
    monkeypatch, fake_page
):
    """Erro/borda: falha real de navegação (DNS, timeout) vira mensagem de
    erro estruturada, nunca exceção crua."""
    fake_page.goto = AsyncMock(side_effect=RuntimeError("net::ERR_NAME_NOT_RESOLVED"))

    result = await browser_tools.browser_navigate.ainvoke(
        {"url": "https://dominio-que-nao-existe-xyz.test"}, config=_config()
    )

    assert result.startswith("Error:")


@pytest.mark.asyncio
async def test_browser_screenshot_returns_data_url_when_preview_running(
    monkeypatch, fake_page
):
    """Preview ativo → screenshot navega pra URL do preview e devolve data URL base64."""
    monkeypatch.setattr(
        browser_tools,
        "resolve_dev_server_url",
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
        browser_tools, "resolve_dev_server_url", AsyncMock(return_value=None)
    )

    result = await browser_tools.browser_screenshot.ainvoke({}, config=_config())

    assert result.startswith("Error:")
    assert "browser_navigate" in result.lower()


@pytest.mark.asyncio
async def test_browser_click_success_and_selector_not_found(monkeypatch, fake_page):
    """Clique bem-sucedido confirma o seletor; seletor inexistente devolve erro claro."""
    monkeypatch.setattr(
        browser_tools,
        "resolve_dev_server_url",
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
        "resolve_dev_server_url",
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
        "resolve_dev_server_url",
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
        "resolve_dev_server_url",
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


# ---------------------------------------------------------------------------
# browser_start/stop/restart/logs (0.7): paridade de controle usuário↔agente
# — o agente ganha as mesmas ações que a aba Preview já oferece ao usuário.
# As tools importam as funções HTTP de backend.api.handlers.workspaces por
# import tardio (dentro do corpo, evita import circular) — o monkeypatch
# tem que mirar o módulo real, não o atributo do módulo de tools.
# ---------------------------------------------------------------------------


def _launch_json(names: list[str]):
    import backend.api.handlers.workspaces as ws_mod

    return ws_mod.LaunchJsonModel(
        configurations=[
            ws_mod.LaunchConfigModel(
                name=n, runtimeExecutable="bun", runtimeArgs=["run", "dev"], port=3000
            )
            for n in names
        ]
    )


class TestResolvePreviewName:
    @pytest.mark.asyncio
    async def test_single_config_auto_resolves_when_name_omitted(self, monkeypatch):
        import backend.api.handlers.workspaces as ws_mod

        monkeypatch.setattr(
            ws_mod, "get_launch_json", AsyncMock(return_value=_launch_json(["web"]))
        )

        name, err = await browser_tools._resolve_dev_server_name("ws1", None)

        assert name == "web"
        assert err == ""

    @pytest.mark.asyncio
    async def test_multiple_configs_without_name_returns_error(self, monkeypatch):
        import backend.api.handlers.workspaces as ws_mod

        monkeypatch.setattr(
            ws_mod,
            "get_launch_json",
            AsyncMock(return_value=_launch_json(["web", "api"])),
        )

        name, err = await browser_tools._resolve_dev_server_name("ws1", None)

        assert name is None
        assert "web" in err and "api" in err

    @pytest.mark.asyncio
    async def test_unknown_name_returns_error(self, monkeypatch):
        import backend.api.handlers.workspaces as ws_mod

        monkeypatch.setattr(
            ws_mod, "get_launch_json", AsyncMock(return_value=_launch_json(["web"]))
        )

        name, err = await browser_tools._resolve_dev_server_name("ws1", "ghost")

        assert name is None
        assert "ghost" in err

    @pytest.mark.asyncio
    async def test_empty_launch_json_returns_clear_error(self, monkeypatch):
        import backend.api.handlers.workspaces as ws_mod

        monkeypatch.setattr(
            ws_mod, "get_launch_json", AsyncMock(return_value=_launch_json([]))
        )

        name, err = await browser_tools._resolve_dev_server_name("ws1", None)

        assert name is None
        assert "launch.json" in err


class TestPreviewStartStopRestartTools:
    @pytest.mark.asyncio
    async def test_preview_start_delegates_to_http_handler(self, monkeypatch):
        import backend.api.handlers.workspaces as ws_mod

        monkeypatch.setattr(
            ws_mod, "get_launch_json", AsyncMock(return_value=_launch_json(["web"]))
        )
        monkeypatch.setattr(
            ws_mod,
            "browser_start",
            AsyncMock(
                return_value=ws_mod.StatusResponse(status="ok", message="rodando")
            ),
        )

        result = await browser_tools.browser_start.ainvoke({}, config=_config())

        assert '"status": "ok"' in result
        assert "rodando" in result

    @pytest.mark.asyncio
    async def test_preview_start_with_ambiguous_name_returns_error_without_calling_http(
        self, monkeypatch
    ):
        import backend.api.handlers.workspaces as ws_mod

        monkeypatch.setattr(
            ws_mod,
            "get_launch_json",
            AsyncMock(return_value=_launch_json(["web", "api"])),
        )
        http_start = AsyncMock()
        monkeypatch.setattr(ws_mod, "browser_start", http_start)

        result = await browser_tools.browser_start.ainvoke({}, config=_config())

        assert result.startswith("Error:")
        http_start.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_preview_stop_delegates_to_http_handler(self, monkeypatch):
        import backend.api.handlers.workspaces as ws_mod

        monkeypatch.setattr(
            ws_mod, "get_launch_json", AsyncMock(return_value=_launch_json(["web"]))
        )
        monkeypatch.setattr(
            ws_mod,
            "browser_stop",
            AsyncMock(
                return_value=ws_mod.StatusResponse(status="ok", message="parado")
            ),
        )

        result = await browser_tools.browser_stop.ainvoke({}, config=_config())

        assert '"status": "ok"' in result
        assert "parado" in result

    @pytest.mark.asyncio
    async def test_preview_restart_stops_then_starts(self, monkeypatch):
        import backend.api.handlers.workspaces as ws_mod

        monkeypatch.setattr(
            ws_mod, "get_launch_json", AsyncMock(return_value=_launch_json(["web"]))
        )
        calls: list[str] = []

        async def _fake_stop(workspace_id, req):
            calls.append("stop")
            return ws_mod.StatusResponse(status="ok", message="parado")

        async def _fake_start(workspace_id, req):
            calls.append("start")
            return ws_mod.StatusResponse(status="ok", message="rodando")

        monkeypatch.setattr(ws_mod, "browser_stop", _fake_stop)
        monkeypatch.setattr(ws_mod, "browser_start", _fake_start)

        result = await browser_tools.browser_restart.ainvoke({}, config=_config())

        assert calls == ["stop", "start"]
        assert '"status": "ok"' in result
        assert "rodando" in result


class TestPreviewLogsTool:
    @pytest.mark.asyncio
    async def test_returns_joined_lines_from_buffer(self, monkeypatch):
        import backend.api.handlers.workspaces as ws_mod

        monkeypatch.setattr(
            ws_mod, "get_launch_json", AsyncMock(return_value=_launch_json(["web"]))
        )
        monkeypatch.setattr(
            ws_mod,
            "browser_logs",
            AsyncMock(
                return_value=ws_mod.BrowserLogsResponse(lines=["compiling...", "ready"])
            ),
        )

        result = await browser_tools.browser_logs.ainvoke({}, config=_config())

        assert result == "compiling...\nready"

    @pytest.mark.asyncio
    async def test_never_started_returns_clear_message_not_empty_string(
        self, monkeypatch
    ):
        import backend.api.handlers.workspaces as ws_mod

        monkeypatch.setattr(
            ws_mod, "get_launch_json", AsyncMock(return_value=_launch_json(["web"]))
        )
        monkeypatch.setattr(
            ws_mod,
            "browser_logs",
            AsyncMock(return_value=ws_mod.BrowserLogsResponse(lines=[])),
        )

        result = await browser_tools.browser_logs.ainvoke({}, config=_config())

        assert result != ""
        assert "web" in result
        assert "nunca foi iniciado" in result

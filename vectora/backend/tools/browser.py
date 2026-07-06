"""Tools de browser automation do agente sobre o preview do workspace (A2).

Todas navegam exclusivamente dentro do dev server que o workspace ativo já
subiu (`.vectora/launch.json` + `preview_start`) — ver
`backend.browser.preview.resolve_preview_url`. Nunca abrem uma URL livre da
internet (isso é papel do `web_search`/`fetch_url`).
"""

from __future__ import annotations

import base64
import logging
from typing import Annotated, Any

from langchain.tools import tool
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg

from backend.browser.preview import resolve_preview_url
from backend.browser.session import get_browser_page

logger = logging.getLogger(__name__)

_NO_PREVIEW_ERROR = (
    "Error: nenhum preview server está rodando neste workspace. "
    "Inicie um (aba Preview ou `preview_start`) antes de usar tools de browser."
)


def _workspace_id(config: RunnableConfig | None) -> str:
    return (
        str((config.get("configurable") or {}).get("workspace_id", ""))
        if config
        else ""
    )


async def _resolve_page(config: RunnableConfig | None) -> tuple[Any, str]:
    """Retorna (page, "") em sucesso, ou (None, error) se não houver preview ativo."""
    workspace_id = _workspace_id(config)
    base_url = await resolve_preview_url(workspace_id)
    if base_url is None:
        return None, _NO_PREVIEW_ERROR
    page = await get_browser_page(workspace_id or "default")
    if page.url == "about:blank":
        await page.goto(base_url, wait_until="domcontentloaded")
    return page, ""


@tool(
    extras={
        "render_hint": "image",
        "category": "browser",
        "destructive": False,
        "icon": "camera",
    }
)
async def browser_screenshot(
    config: Annotated[RunnableConfig, InjectedToolArg] = None,  # ty: ignore[invalid-parameter-default]
) -> str:
    """Tira um screenshot da página atual do preview (base64 PNG, data URL).

    Returns:
        Data URL `data:image/png;base64,...` ou mensagem de erro.
    """
    page, err = await _resolve_page(config)
    if page is None:
        return err
    try:
        png_bytes = await page.screenshot(type="png")
        encoded = base64.b64encode(png_bytes).decode("ascii")
        return f"data:image/png;base64,{encoded}"
    except Exception:
        logger.exception("browser_screenshot failed")
        return "Error: falha ao capturar screenshot. Veja logs."


@tool(
    extras={
        "render_hint": "text",
        "category": "browser",
        "destructive": False,
        "icon": "mouse-pointer-click",
    }
)
async def browser_click(
    selector: str,
    config: Annotated[RunnableConfig, InjectedToolArg] = None,  # ty: ignore[invalid-parameter-default]
) -> str:
    """Clica no elemento do preview que casa com o seletor CSS.

    Args:
        selector: Seletor CSS (ex.: "button.submit", "#login-form input[type=email]")

    Returns:
        Confirmação ou mensagem de erro (seletor não encontrado, etc.)
    """
    page, err = await _resolve_page(config)
    if page is None:
        return err
    try:
        await page.click(selector, timeout=5000)
        return f"[OK] Clicado: {selector}"
    except Exception:
        logger.exception("browser_click failed", extra={"selector": selector})
        return f"Error: não foi possível clicar em '{selector}' (elemento não encontrado ou não clicável)."


@tool(
    extras={
        "render_hint": "text",
        "category": "browser",
        "destructive": False,
        "icon": "scroll",
    }
)
async def browser_scroll(
    direction: str = "down",
    amount: int = 600,
    config: Annotated[RunnableConfig, InjectedToolArg] = None,  # ty: ignore[invalid-parameter-default]
) -> str:
    """Rola a página do preview.

    Args:
        direction: "down" ou "up"
        amount: pixels a rolar

    Returns:
        Confirmação ou mensagem de erro.
    """
    page, err = await _resolve_page(config)
    if page is None:
        return err
    if direction not in ("down", "up"):
        return "Error: `direction` deve ser 'down' ou 'up'."
    try:
        delta = amount if direction == "down" else -amount
        await page.mouse.wheel(0, delta)
        return f"[OK] Rolado {direction} ({amount}px)"
    except Exception:
        logger.exception("browser_scroll failed")
        return "Error: falha ao rolar a página. Veja logs."


@tool(
    extras={
        "render_hint": "text",
        "category": "browser",
        "destructive": True,
        "icon": "keyboard",
    }
)
async def browser_fill(
    selector: str,
    value: str,
    config: Annotated[RunnableConfig, InjectedToolArg] = None,  # ty: ignore[invalid-parameter-default]
) -> str:
    """Preenche um campo do preview (input/textarea) com o valor indicado.

    Args:
        selector: Seletor CSS do campo
        value: Texto a preencher

    Returns:
        Confirmação ou mensagem de erro.
    """
    page, err = await _resolve_page(config)
    if page is None:
        return err
    try:
        await page.fill(selector, value, timeout=5000)
        return f"[OK] Preenchido: {selector}"
    except Exception:
        logger.exception("browser_fill failed", extra={"selector": selector})
        return (
            f"Error: não foi possível preencher '{selector}' (elemento não encontrado)."
        )


@tool(
    extras={
        "render_hint": "code_block",
        "category": "browser",
        "destructive": False,
        "icon": "file-text",
    }
)
async def browser_read_dom(
    selector: str = "body",
    config: Annotated[RunnableConfig, InjectedToolArg] = None,  # ty: ignore[invalid-parameter-default]
) -> str:
    """Lê o texto visível do preview (não o HTML cru).

    Args:
        selector: Seletor CSS da raiz da leitura (padrão: página inteira)

    Returns:
        Texto visível do elemento, ou mensagem de erro se o seletor não existir.
    """
    page, err = await _resolve_page(config)
    if page is None:
        return err
    try:
        text = await page.inner_text(selector, timeout=5000)
        return text or "(vazio)"
    except Exception:
        logger.exception("browser_read_dom failed", extra={"selector": selector})
        return f"Error: seletor '{selector}' não encontrado no preview."

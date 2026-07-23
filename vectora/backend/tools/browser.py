"""Tools de browser do agente: automação sobre a página atual (dev server
local do workspace OU qualquer URL http/https navegada livremente) mais
gestão dos dev servers declarados em `.vectora/launch.json`.

`browser_navigate` é a porta de entrada pra navegação livre — nenhum
guardrail de host/porta, só esquema (`http`/`https`). As demais tools de
automação (`browser_click`/`browser_fill`/etc.) operam sobre a página já
carregada na sessão Playwright persistente do workspace
(`backend.browser.session.get_browser_page`); se nada foi navegado ainda,
caem no dev server ativo do workspace (mesmo fallback de sempre).
"""

from __future__ import annotations

import base64
import json
import logging
from typing import Annotated, Any
from urllib.parse import urlparse

from langchain.tools import tool
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg

from backend.browser.dev_server import resolve_dev_server_url
from backend.browser.session import get_browser_page, has_browser_session

logger = logging.getLogger(__name__)

_NO_PAGE_ERROR = (
    "Error: nenhuma página aberta neste workspace. Use `browser_navigate` "
    "(URL livre) ou inicie um dev server (`browser_start`) antes de usar "
    "tools de browser."
)

_ALLOWED_SCHEMES = ("http", "https")


def _workspace_id(config: RunnableConfig | None) -> str:
    return (
        str((config.get("configurable") or {}).get("workspace_id", ""))
        if config
        else ""
    )


async def _resolve_page(config: RunnableConfig | None) -> tuple[Any, str]:
    """Retorna (page, "") em sucesso, ou (None, error) se não houver página
    resolvível — nem já navegada, nem dev server ativo do workspace.

    Só lança um browser Playwright novo (`get_browser_page`) quando já tem
    algo pra mostrar nele — uma sessão existente (navegação anterior via
    `browser_navigate`) ou um dev server confirmado — nunca à toa.
    """
    workspace_id = _workspace_id(config)
    session_key = workspace_id or "default"
    if has_browser_session(session_key):
        page = await get_browser_page(session_key)
        if page.url != "about:blank":
            return page, ""
        base_url = await resolve_dev_server_url(workspace_id)
        if base_url is None:
            return None, _NO_PAGE_ERROR
        await page.goto(base_url, wait_until="domcontentloaded")
        return page, ""

    base_url = await resolve_dev_server_url(workspace_id)
    if base_url is None:
        return None, _NO_PAGE_ERROR
    page = await get_browser_page(session_key)
    await page.goto(base_url, wait_until="domcontentloaded")
    return page, ""


@tool(
    extras={
        "render_hint": "text",
        "category": "browser",
        "destructive": False,
        "icon": "globe",
    }
)
async def browser_navigate(
    url: str,
    config: Annotated[RunnableConfig, InjectedToolArg] = None,  # ty: ignore[invalid-parameter-default]
) -> str:
    """Navega a página do browser do workspace pra qualquer URL http(s) —
    site externo (Google, GitHub, docs, ...) ou dev server local, sem
    depender de nenhum servidor já rodando.

    Args:
        url: URL completa (`http://` ou `https://`) a navegar.

    Returns:
        Confirmação com a URL final carregada, ou mensagem de erro
        (esquema não permitido, timeout, DNS, etc.)
    """
    scheme = urlparse(url).scheme.lower()
    if scheme not in _ALLOWED_SCHEMES:
        return (
            f"Error: esquema {scheme!r} não permitido — só http:// e "
            "https:// são aceitos pra navegação."
        )
    workspace_id = _workspace_id(config)
    try:
        page = await get_browser_page(workspace_id or "default")
        await page.goto(url, wait_until="domcontentloaded", timeout=15000)
        return f"[OK] Navegado para {page.url}"
    except Exception:
        logger.exception("browser_navigate failed", extra={"url": url})
        return f"Error: falha ao navegar para {url!r}. Veja logs."


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
    """Tira um screenshot da página atual do browser (base64 PNG, data URL).

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
    """Clica no elemento da página atual que casa com o seletor CSS.

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
    """Rola a página atual do browser.

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
    """Preenche um campo da página atual (input/textarea) com o valor indicado.

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
    """Lê o texto visível da página atual (não o HTML cru).

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
        return f"Error: seletor '{selector}' não encontrado na página."


async def _resolve_dev_server_name(
    workspace_id: str, name: str | None
) -> tuple[str | None, str]:
    """Resolve qual configuração de `.vectora/launch.json` usar.

    Retorna `(name, "")` em sucesso, ou `(None, mensagem_de_erro)` — nunca
    adivinha entre múltiplas configs ambíguas.
    """
    from backend.api.handlers.workspaces import get_launch_json

    launch = await get_launch_json(workspace_id)
    if not launch.configurations:
        return (
            None,
            "Error: nenhuma configuração de dev server encontrada "
            "(.vectora/launch.json vazio ou ausente).",
        )
    if name:
        if not any(c.name == name for c in launch.configurations):
            available = ", ".join(c.name for c in launch.configurations)
            return (
                None,
                f"Error: configuração '{name}' não encontrada. Disponíveis: {available}.",
            )
        return name, ""
    if len(launch.configurations) == 1:
        return launch.configurations[0].name, ""
    available = ", ".join(c.name for c in launch.configurations)
    return (
        None,
        f"Error: múltiplas configurações de dev server existem ({available}) "
        "— especifique `name`.",
    )


@tool(
    extras={
        "render_hint": "json",
        "category": "browser",
        "destructive": False,
        "icon": "play",
    }
)
async def browser_start(
    name: str | None = None,
    config: Annotated[RunnableConfig, InjectedToolArg] = None,  # ty: ignore[invalid-parameter-default]
) -> str:
    """Inicia o dev server do workspace ativo (mesmo efeito que o usuário
    clicar em "play" na aba Browser).

    Args:
        name: Nome da configuração em `.vectora/launch.json`. Se omitido e
            houver só uma configuração, usa ela; se houver mais de uma,
            retorna erro pedindo pra especificar.

    Returns:
        JSON `{"status": "ok"|"pending"|"error", "message": "..."}`. Em
        `"pending"`/`"error"`, chame `browser_logs` pra ver a saída real do
        processo antes de tentar de novo.
    """
    from backend.api.handlers.workspaces import BrowserStartRequest
    from backend.api.handlers.workspaces import browser_start as _http_browser_start

    workspace_id = _workspace_id(config)
    resolved_name, err = await _resolve_dev_server_name(workspace_id, name)
    if resolved_name is None:
        return err
    result = await _http_browser_start(
        workspace_id, BrowserStartRequest(name=resolved_name)
    )
    return json.dumps({"status": result.status, "message": result.message})


@tool(
    extras={
        "render_hint": "json",
        "category": "browser",
        "destructive": False,
        "icon": "square",
    }
)
async def browser_stop(
    name: str | None = None,
    config: Annotated[RunnableConfig, InjectedToolArg] = None,  # ty: ignore[invalid-parameter-default]
) -> str:
    """Para o dev server do workspace ativo.

    Args:
        name: Nome da configuração em `.vectora/launch.json` (mesma regra de
            resolução de `browser_start`).

    Returns:
        JSON `{"status": "ok"|"error", "message": "..."}`.
    """
    from backend.api.handlers.workspaces import BrowserStopRequest
    from backend.api.handlers.workspaces import browser_stop as _http_browser_stop

    workspace_id = _workspace_id(config)
    resolved_name, err = await _resolve_dev_server_name(workspace_id, name)
    if resolved_name is None:
        return err
    result = await _http_browser_stop(
        workspace_id, BrowserStopRequest(name=resolved_name)
    )
    return json.dumps({"status": result.status, "message": result.message})


@tool(
    extras={
        "render_hint": "json",
        "category": "browser",
        "destructive": False,
        "icon": "refresh-cw",
    }
)
async def browser_restart(
    name: str | None = None,
    config: Annotated[RunnableConfig, InjectedToolArg] = None,  # ty: ignore[invalid-parameter-default]
) -> str:
    """Reinicia o dev server (para se estiver rodando, depois inicia de
    novo) — útil depois de corrigir a causa de uma falha (ex.: rodar
    `bun install`) pra confirmar que resolveu.

    Args:
        name: Nome da configuração em `.vectora/launch.json` (mesma regra de
            resolução de `browser_start`).

    Returns:
        JSON `{"status": "ok"|"pending"|"error", "message": "..."}` do novo
        start.
    """
    from backend.api.handlers.workspaces import BrowserStartRequest, BrowserStopRequest
    from backend.api.handlers.workspaces import browser_start as _http_browser_start
    from backend.api.handlers.workspaces import browser_stop as _http_browser_stop

    workspace_id = _workspace_id(config)
    resolved_name, err = await _resolve_dev_server_name(workspace_id, name)
    if resolved_name is None:
        return err
    await _http_browser_stop(workspace_id, BrowserStopRequest(name=resolved_name))
    result = await _http_browser_start(
        workspace_id, BrowserStartRequest(name=resolved_name)
    )
    return json.dumps({"status": result.status, "message": result.message})


@tool(
    extras={
        "render_hint": "terminal_output",
        "category": "browser",
        "destructive": False,
        "icon": "terminal",
    }
)
async def browser_logs(
    name: str | None = None,
    lines: int = 100,
    config: Annotated[RunnableConfig, InjectedToolArg] = None,  # ty: ignore[invalid-parameter-default]
) -> str:
    """Lê as últimas linhas de stdout/stderr do dev server — inclusive
    depois dele ter travado/morrido (o histórico não é apagado ao parar).
    Use pra se autodiagnosticar quando `browser_start` retornar
    `"error"`/`"pending"`, ou quando as tools de automação
    (`browser_screenshot` etc.) falharem.

    Args:
        name: Nome da configuração em `.vectora/launch.json` (mesma regra de
            resolução de `browser_start`).
        lines: Quantidade de linhas mais recentes a retornar (padrão 100).

    Returns:
        As últimas `lines` linhas de saída, ou uma mensagem indicando que
        esse dev server nunca foi iniciado.
    """
    from backend.api.handlers.workspaces import browser_logs as _http_browser_logs

    workspace_id = _workspace_id(config)
    resolved_name, err = await _resolve_dev_server_name(workspace_id, name)
    if resolved_name is None:
        return err
    result = await _http_browser_logs(workspace_id, resolved_name)
    if not result.lines:
        return (
            f"(nenhum log disponível — dev server '{resolved_name}' nunca foi iniciado)"
        )
    return "\n".join(result.lines[-lines:])

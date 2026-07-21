"""Tools de browser automation do agente sobre o preview do workspace (A2).

Todas navegam exclusivamente dentro do dev server que o workspace ativo já
subiu (`.vectora/launch.json` + `preview_start`) — ver
`backend.browser.preview.resolve_preview_url`. Nunca abrem uma URL livre da
internet (isso é papel do `web_search`/`fetch_url`).
"""

from __future__ import annotations

import base64
import json
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


async def _resolve_preview_name(
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
            "Error: nenhuma configuração de preview encontrada "
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
        f"Error: múltiplas configurações de preview existem ({available}) "
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
async def preview_start(
    name: str | None = None,
    config: Annotated[RunnableConfig, InjectedToolArg] = None,  # ty: ignore[invalid-parameter-default]
) -> str:
    """Inicia o dev server de preview do workspace ativo (mesmo efeito que o
    usuário clicar em "play" na aba Preview).

    Args:
        name: Nome da configuração em `.vectora/launch.json`. Se omitido e
            houver só uma configuração, usa ela; se houver mais de uma,
            retorna erro pedindo pra especificar.

    Returns:
        JSON `{"status": "ok"|"pending"|"error", "message": "..."}`. Em
        `"pending"`/`"error"`, chame `preview_logs` pra ver a saída real do
        processo antes de tentar de novo.
    """
    from backend.api.handlers.workspaces import PreviewStartRequest
    from backend.api.handlers.workspaces import preview_start as _http_preview_start

    workspace_id = _workspace_id(config)
    resolved_name, err = await _resolve_preview_name(workspace_id, name)
    if resolved_name is None:
        return err
    result = await _http_preview_start(
        workspace_id, PreviewStartRequest(name=resolved_name)
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
async def preview_stop(
    name: str | None = None,
    config: Annotated[RunnableConfig, InjectedToolArg] = None,  # ty: ignore[invalid-parameter-default]
) -> str:
    """Para o dev server de preview do workspace ativo.

    Args:
        name: Nome da configuração em `.vectora/launch.json` (mesma regra de
            resolução de `preview_start`).

    Returns:
        JSON `{"status": "ok"|"error", "message": "..."}`.
    """
    from backend.api.handlers.workspaces import PreviewStopRequest
    from backend.api.handlers.workspaces import preview_stop as _http_preview_stop

    workspace_id = _workspace_id(config)
    resolved_name, err = await _resolve_preview_name(workspace_id, name)
    if resolved_name is None:
        return err
    result = await _http_preview_stop(
        workspace_id, PreviewStopRequest(name=resolved_name)
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
async def preview_restart(
    name: str | None = None,
    config: Annotated[RunnableConfig, InjectedToolArg] = None,  # ty: ignore[invalid-parameter-default]
) -> str:
    """Reinicia o dev server de preview (para se estiver rodando, depois
    inicia de novo) — útil depois de corrigir a causa de uma falha (ex.:
    rodar `bun install`) pra confirmar que resolveu.

    Args:
        name: Nome da configuração em `.vectora/launch.json` (mesma regra de
            resolução de `preview_start`).

    Returns:
        JSON `{"status": "ok"|"pending"|"error", "message": "..."}` do novo
        start.
    """
    from backend.api.handlers.workspaces import PreviewStartRequest, PreviewStopRequest
    from backend.api.handlers.workspaces import preview_start as _http_preview_start
    from backend.api.handlers.workspaces import preview_stop as _http_preview_stop

    workspace_id = _workspace_id(config)
    resolved_name, err = await _resolve_preview_name(workspace_id, name)
    if resolved_name is None:
        return err
    await _http_preview_stop(workspace_id, PreviewStopRequest(name=resolved_name))
    result = await _http_preview_start(
        workspace_id, PreviewStartRequest(name=resolved_name)
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
async def preview_logs(
    name: str | None = None,
    lines: int = 100,
    config: Annotated[RunnableConfig, InjectedToolArg] = None,  # ty: ignore[invalid-parameter-default]
) -> str:
    """Lê as últimas linhas de stdout/stderr do dev server de preview —
    inclusive depois dele ter travado/morrido (o histórico não é apagado ao
    parar). Use pra se autodiagnosticar quando `preview_start` retornar
    `"error"`/`"pending"`, ou quando as tools de browser automation
    (`browser_screenshot` etc.) falharem.

    Args:
        name: Nome da configuração em `.vectora/launch.json` (mesma regra de
            resolução de `preview_start`).
        lines: Quantidade de linhas mais recentes a retornar (padrão 100).

    Returns:
        As últimas `lines` linhas de saída, ou uma mensagem indicando que
        esse preview nunca foi iniciado.
    """
    from backend.api.handlers.workspaces import preview_logs as _http_preview_logs

    workspace_id = _workspace_id(config)
    resolved_name, err = await _resolve_preview_name(workspace_id, name)
    if resolved_name is None:
        return err
    result = await _http_preview_logs(workspace_id, resolved_name)
    if not result.lines:
        return f"(nenhum log disponível — preview '{resolved_name}' nunca foi iniciado)"
    return "\n".join(result.lines[-lines:])

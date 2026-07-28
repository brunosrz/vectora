"""Tools de observabilidade e controle avançado do browser Chromium do
agente (CDP) — distinto de `backend/tools/browser.py`, que cobre só
navegação/interação básica (click/fill/scroll/screenshot) e gestão de dev
server. Aqui: múltiplas abas, console/network logs, `evaluate` de JS
arbitrário, dialogs, emulação, tracing de performance, heap snapshot e
Lighthouse.
"""

from __future__ import annotations

import json
import logging
from typing import Annotated

from langchain.tools import tool
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg

from backend.browser.session import (
    close_tab,
    get_tab_state,
    has_browser_session,
    list_tabs,
    new_tab,
    select_tab,
)

logger = logging.getLogger(__name__)


def _workspace_id(config: RunnableConfig | None) -> str:
    raw = (
        str((config.get("configurable") or {}).get("workspace_id", ""))
        if config
        else ""
    )
    return raw or "default"


_NO_SESSION_ERROR = json.dumps(
    {
        "status": "error",
        "error": (
            "Nenhuma sessão de browser aberta neste workspace. Use "
            "`browser_navigate` ou `browser_new_tab` primeiro."
        ),
    }
)


@tool(
    extras={
        "render_hint": "json",
        "category": "browser",
        "destructive": False,
        "icon": "layout-grid",
    }
)
async def browser_list_tabs(
    config: Annotated[RunnableConfig, InjectedToolArg] = None,  # ty: ignore[invalid-parameter-default]
) -> str:
    """Lista as abas abertas na sessão de browser do workspace ativo.

    Returns:
        JSON `{"tabs": [{"tab_id", "url", "active"}, ...]}`.
    """
    workspace_id = _workspace_id(config)
    tabs = await list_tabs(workspace_id)
    return json.dumps({"tabs": tabs})


@tool(
    extras={
        "render_hint": "text",
        "category": "browser",
        "destructive": False,
        "icon": "plus-square",
    }
)
async def browser_new_tab(
    url: str | None = None,
    config: Annotated[RunnableConfig, InjectedToolArg] = None,  # ty: ignore[invalid-parameter-default]
) -> str:
    """Abre uma aba nova na sessão do workspace ativo (lança o browser se
    ainda não houver sessão) e a torna a aba ativa.

    Args:
        url: URL http(s) opcional pra já navegar a aba nova.

    Returns:
        JSON `{"status": "ok", "tab_id": "..."}` ou erro.
    """
    workspace_id = _workspace_id(config)
    try:
        tab_id = await new_tab(workspace_id, url=url)
        return json.dumps({"status": "ok", "tab_id": tab_id})
    except Exception as exc:
        logger.exception("browser_new_tab failed", extra={"url": url})
        return json.dumps({"status": "error", "error": str(exc)})


@tool(
    extras={
        "render_hint": "text",
        "category": "browser",
        "destructive": True,
        "icon": "x-square",
    }
)
async def browser_close_tab(
    tab_id: str,
    config: Annotated[RunnableConfig, InjectedToolArg] = None,  # ty: ignore[invalid-parameter-default]
) -> str:
    """Fecha uma aba pelo id. Nunca deixa a sessão sem nenhuma aba —
    fechar a última abre uma em branco no lugar.

    Args:
        tab_id: id da aba (de `browser_list_tabs`).
    """
    workspace_id = _workspace_id(config)
    if not has_browser_session(workspace_id):
        return _NO_SESSION_ERROR
    ok = await close_tab(workspace_id, tab_id)
    if not ok:
        return json.dumps(
            {"status": "error", "error": f"aba '{tab_id}' não encontrada"}
        )
    return json.dumps({"status": "ok", "tab_id": tab_id})


@tool(
    extras={
        "render_hint": "text",
        "category": "browser",
        "destructive": False,
        "icon": "layout-panel-left",
    }
)
async def browser_select_tab(
    tab_id: str,
    config: Annotated[RunnableConfig, InjectedToolArg] = None,  # ty: ignore[invalid-parameter-default]
) -> str:
    """Torna `tab_id` a aba ativa da sessão — as demais tools de browser
    (`browser_click`, `browser_screenshot`, etc.) passam a operar nela.

    Args:
        tab_id: id da aba (de `browser_list_tabs`).
    """
    workspace_id = _workspace_id(config)
    if not has_browser_session(workspace_id):
        return _NO_SESSION_ERROR
    ok = await select_tab(workspace_id, tab_id)
    if not ok:
        return json.dumps(
            {"status": "error", "error": f"aba '{tab_id}' não encontrada"}
        )
    return json.dumps({"status": "ok", "tab_id": tab_id})


@tool(
    extras={
        "render_hint": "json",
        "category": "browser",
        "destructive": False,
        "icon": "terminal",
    }
)
async def browser_list_console_messages(
    tab_id: str | None = None,
    limit: int = 50,
    config: Annotated[RunnableConfig, InjectedToolArg] = None,  # ty: ignore[invalid-parameter-default]
) -> str:
    """Lista as mensagens de console (log/warn/error/...) capturadas da aba
    desde que ela foi aberta.

    Args:
        tab_id: id da aba (padrão: aba ativa).
        limit: máximo de mensagens mais recentes a retornar.

    Returns:
        JSON `{"messages": [{"type", "text"}, ...]}`.
    """
    workspace_id = _workspace_id(config)
    tab = get_tab_state(workspace_id, tab_id)
    if tab is None:
        return _NO_SESSION_ERROR
    messages = list(tab.console_log)[-limit:]
    return json.dumps({"messages": messages})


@tool(
    extras={
        "render_hint": "text",
        "category": "browser",
        "destructive": True,
        "icon": "eraser",
    }
)
async def browser_clear_console(
    tab_id: str | None = None,
    config: Annotated[RunnableConfig, InjectedToolArg] = None,  # ty: ignore[invalid-parameter-default]
) -> str:
    """Limpa o buffer de mensagens de console capturadas da aba (não afeta
    o console real do browser, só o histórico que o agente lê).

    Args:
        tab_id: id da aba (padrão: aba ativa).
    """
    workspace_id = _workspace_id(config)
    tab = get_tab_state(workspace_id, tab_id)
    if tab is None:
        return _NO_SESSION_ERROR
    tab.console_log.clear()
    return json.dumps({"status": "ok"})


@tool(
    extras={
        "render_hint": "json",
        "category": "browser",
        "destructive": False,
        "icon": "network",
    }
)
async def browser_list_network_requests(
    tab_id: str | None = None,
    resource_type: str | None = None,
    limit: int = 50,
    config: Annotated[RunnableConfig, InjectedToolArg] = None,  # ty: ignore[invalid-parameter-default]
) -> str:
    """Lista as requisições de rede capturadas da aba desde que foi aberta.

    Args:
        tab_id: id da aba (padrão: aba ativa).
        resource_type: filtra por tipo (ex.: "xhr", "fetch", "document",
            "script", "stylesheet", "image") — omitido lista todos.
        limit: máximo de requisições mais recentes a retornar.

    Returns:
        JSON `{"requests": [{"request_id", "url", "method",
        "resource_type", "status"}, ...]}`.
    """
    workspace_id = _workspace_id(config)
    tab = get_tab_state(workspace_id, tab_id)
    if tab is None:
        return _NO_SESSION_ERROR
    entries = list(tab.network_log)
    if resource_type:
        entries = [e for e in entries if e.get("resource_type") == resource_type]
    return json.dumps({"requests": entries[-limit:]})


@tool(
    extras={
        "render_hint": "json",
        "category": "browser",
        "destructive": False,
        "icon": "network",
    }
)
async def browser_get_network_request(
    request_id: str,
    tab_id: str | None = None,
    config: Annotated[RunnableConfig, InjectedToolArg] = None,  # ty: ignore[invalid-parameter-default]
) -> str:
    """Detalhes de uma requisição de rede específica, pelo `request_id`
    retornado por `browser_list_network_requests`.

    Args:
        request_id: id da requisição.
        tab_id: id da aba (padrão: aba ativa).
    """
    workspace_id = _workspace_id(config)
    tab = get_tab_state(workspace_id, tab_id)
    if tab is None:
        return _NO_SESSION_ERROR
    for entry in tab.network_log:
        if entry.get("request_id") == request_id:
            return json.dumps(entry)
    return json.dumps(
        {"status": "error", "error": f"request '{request_id}' não encontrada"}
    )

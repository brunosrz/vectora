"""resolve_dev_server_url: só aponta pra dev servers que o workspace já subiu."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.browser.dev_server import resolve_dev_server_url


@pytest.mark.asyncio
async def test_resolve_dev_server_url_returns_port_of_running_server(monkeypatch):
    cfg = MagicMock()
    cfg.configurations = [MagicMock(name="web", port=5173)]
    cfg.configurations[0].name = "web"

    running_proc = MagicMock(returncode=None)

    import backend.api.handlers.workspaces as workspaces_mod

    monkeypatch.setattr(workspaces_mod, "get_launch_json", AsyncMock(return_value=cfg))
    monkeypatch.setattr(workspaces_mod, "_browser_procs", {"ws1::web": running_proc})
    monkeypatch.setattr(workspaces_mod, "_is_port_open", AsyncMock(return_value=True))

    url = await resolve_dev_server_url("ws1")

    assert url == "http://localhost:5173"


@pytest.mark.asyncio
async def test_resolve_dev_server_url_returns_none_when_process_alive_but_port_closed(
    monkeypatch,
):
    """Bug reproduzido ao vivo: processo do dev server já existe (recém
    spawnado) mas ainda não terminou de compilar/bindar a porta — navegar
    pra lá cedo demais dá ERR_CONNECTION_REFUSED. `resolve_dev_server_url` só
    deve considerar "pronto" com a porta de fato aceitando conexão."""
    cfg = MagicMock()
    cfg.configurations = [MagicMock(name="web", port=5173)]
    cfg.configurations[0].name = "web"

    running_proc = MagicMock(returncode=None)

    import backend.api.handlers.workspaces as workspaces_mod

    monkeypatch.setattr(workspaces_mod, "get_launch_json", AsyncMock(return_value=cfg))
    monkeypatch.setattr(workspaces_mod, "_browser_procs", {"ws1::web": running_proc})
    monkeypatch.setattr(workspaces_mod, "_is_port_open", AsyncMock(return_value=False))

    url = await resolve_dev_server_url("ws1")

    assert url is None


@pytest.mark.asyncio
async def test_resolve_dev_server_url_returns_none_when_nothing_running(monkeypatch):
    cfg = MagicMock()
    cfg.configurations = []

    import backend.api.handlers.workspaces as workspaces_mod

    monkeypatch.setattr(workspaces_mod, "get_launch_json", AsyncMock(return_value=cfg))

    url = await resolve_dev_server_url("ws-sem-dev-server")

    assert url is None

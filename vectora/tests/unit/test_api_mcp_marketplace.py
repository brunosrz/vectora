"""TDD — MCP Marketplace (FASE 5.3).

GET  /mcp/registry  — lista conectores disponíveis
POST /mcp/install   — registra um MCP no workspace
POST /mcp/uninstall — remove um MCP do workspace
"""

from __future__ import annotations

import pytest

from backend.api.handlers.mcp_marketplace import (
    _REGISTRY,
    InstallRequest,
    MCPConnector,
    UninstallRequest,
    install_mcp,
    list_registry,
    uninstall_mcp,
)


def test_registry_is_not_empty():
    """O registry embutido deve ter pelo menos alguns conectores."""
    assert len(_REGISTRY) > 0


def test_registry_entries_have_required_fields():
    """Cada entrada do registry deve ter id, name e description."""
    for entry in _REGISTRY:
        assert entry.id, "id não pode ser vazio"
        assert entry.name, "name não pode ser vazio"
        assert entry.description, "description não pode ser vazio"


def test_list_registry_returns_all_connectors():
    """list_registry deve retornar todos os conectores."""
    result = list_registry()
    assert len(result) == len(_REGISTRY)


def test_list_registry_items_are_mcp_connectors():
    """list_registry deve retornar instâncias de MCPConnector."""
    result = list_registry()
    assert all(isinstance(c, MCPConnector) for c in result)


@pytest.mark.asyncio
async def test_install_mcp_known_connector(tmp_path, monkeypatch):
    """Instalar um conector conhecido deve retornar status installed."""
    monkeypatch.setattr(
        "backend.api.handlers.mcp_marketplace._config_path",
        lambda: tmp_path / "mcp.json",
    )
    req = InstallRequest(mcp_id=_REGISTRY[0].id)
    result = await install_mcp(req)
    assert result["status"] in ("ok", "installed")


@pytest.mark.asyncio
async def test_install_mcp_unknown_connector_returns_error(tmp_path, monkeypatch):
    """Instalar um conector desconhecido deve retornar status error."""
    monkeypatch.setattr(
        "backend.api.handlers.mcp_marketplace._config_path",
        lambda: tmp_path / "mcp.json",
    )
    req = InstallRequest(mcp_id="does-not-exist-xyz")
    result = await install_mcp(req)
    assert result.get("status") == "error" or "error" in result


@pytest.mark.asyncio
async def test_uninstall_mcp_returns_ok(tmp_path, monkeypatch):
    """Desinstalar (mesmo que não instalado) deve retornar ok."""
    monkeypatch.setattr(
        "backend.api.handlers.mcp_marketplace._config_path",
        lambda: tmp_path / "mcp.json",
    )
    req = UninstallRequest(mcp_id=_REGISTRY[0].id)
    result = await uninstall_mcp(req)
    assert result["status"] in ("ok", "removed", "not_found")

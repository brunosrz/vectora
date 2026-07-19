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
    _connector_to_server,
    _req_user_id,
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


@pytest.fixture
def _functional_store(tmp_path, monkeypatch):
    """Aponta o store MCP funcional (plugins) para um dir temporário isolado."""
    from backend.workspace import plugins

    monkeypatch.setattr(plugins, "_plugins_dir", lambda: tmp_path / "mcp")
    monkeypatch.setattr(plugins, "_versions", {})
    monkeypatch.setattr(plugins, "_mcp_tools_cache", {})
    monkeypatch.setattr(plugins, "publish_soon", lambda *a, **k: None, raising=False)
    return plugins


@pytest.mark.asyncio
async def test_install_wires_into_functional_store_and_tools(
    _functional_store, monkeypatch
):
    """Sprint 4.1: instalar um conector grava no MESMO store que o agente lê
    (plugins), então get_user_mcp_tools passa a incluir as tools dele — antes o
    install gravava num mcp.json paralelo que ninguém lia."""
    plugins = _functional_store

    req = InstallRequest(mcp_id=_REGISTRY[0].id)
    result = await install_mcp(req, user_id="local")
    assert result["status"] == "installed"

    # Registrado no store funcional por-usuário.
    servers = plugins.list_servers("local")
    assert any(s.name == _REGISTRY[0].id for s in servers)

    # E as tools do servidor entram no toolset via get_user_mcp_tools.
    class _FakeTool:
        def __init__(self, name):
            self.name = name

    class _FakeClient:
        def __init__(self, connections):
            self.connections = connections

        async def get_tools(self):
            return [_FakeTool("brave_web_search")]

    monkeypatch.setattr(plugins, "MultiServerMCPClient", _FakeClient)
    tools = await plugins.get_user_mcp_tools("local")
    assert [t.name for t in tools] == ["brave_web_search"]


@pytest.mark.asyncio
async def test_install_mcp_unknown_connector_returns_error(_functional_store):
    """Erro/borda: conector desconhecido → status error, nada gravado."""
    result = await install_mcp(InstallRequest(mcp_id="does-not-exist-xyz"))
    assert result.get("status") == "error"
    assert _functional_store.list_servers("local") == []


@pytest.mark.asyncio
async def test_uninstall_removes_from_functional_store(_functional_store):
    """Desinstalar remove do store funcional; remover o que não existe →
    not_found (não erro)."""
    plugins = _functional_store
    await install_mcp(InstallRequest(mcp_id=_REGISTRY[0].id), user_id="local")
    assert plugins.list_servers("local")

    removed = await uninstall_mcp(UninstallRequest(mcp_id=_REGISTRY[0].id), "local")
    assert removed["status"] == "removed"
    assert plugins.list_servers("local") == []

    again = await uninstall_mcp(UninstallRequest(mcp_id=_REGISTRY[0].id), "local")
    assert again["status"] == "not_found"


def test_connector_to_server_com_install_cmd_vazio():
    """Erro/borda: conector sem install_cmd (string vazia) cai no fallback
    ["npx"] sem args, em vez de estourar IndexError no split()[0]."""
    connector = MCPConnector(id="custom", name="Custom", description="x")
    server = _connector_to_server(connector)
    assert server.command == "npx"
    assert server.args == []
    assert server.name == "custom"


def test_req_user_id_extrai_do_request_state_ou_usa_fallback_local():
    """_req_user_id lê request.state.user.id quando presente; sem usuário
    autenticado no state, cai no fallback 'local' (uso desktop single-user)."""
    from types import SimpleNamespace
    from typing import Any

    req_autenticado: Any = SimpleNamespace(
        state=SimpleNamespace(user=SimpleNamespace(id="uuid-123"))
    )
    assert _req_user_id(req_autenticado) == "uuid-123"

    req_sem_user: Any = SimpleNamespace(state=SimpleNamespace(user=None))
    assert _req_user_id(req_sem_user) == "local"


@pytest.mark.asyncio
async def test_install_uninstall_mcp_tratam_excecao_do_store(
    _functional_store, monkeypatch
):
    """Erro/borda: plugins.add_server/remove_server lançando não deve propagar
    — install_mcp/uninstall_mcp devolvem status='error' (tools defensivas §11)."""

    def _boom_add(*a, **k):
        raise RuntimeError("disco cheio")

    def _boom_remove(*a, **k):
        raise RuntimeError("arquivo corrompido")

    monkeypatch.setattr(_functional_store, "add_server", _boom_add)
    out_install = await install_mcp(InstallRequest(mcp_id=_REGISTRY[0].id))
    assert out_install["status"] == "error"
    assert "disco cheio" in out_install["error"]

    monkeypatch.setattr(_functional_store, "remove_server", _boom_remove)
    out_uninstall = await uninstall_mcp(UninstallRequest(mcp_id=_REGISTRY[0].id))
    assert out_uninstall["status"] == "error"
    assert "arquivo corrompido" in out_uninstall["error"]

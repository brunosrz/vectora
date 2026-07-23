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


@pytest.fixture
def _no_remote_registry(monkeypatch):
    """Isola os testes dos dois registries remotos reais (Vectora + oficial
    de MCP) — sem rede nos testes unitários."""
    from unittest.mock import AsyncMock

    from backend.api.handlers import mcp_marketplace

    monkeypatch.setattr(
        mcp_marketplace.registry_client, "fetch_catalog", AsyncMock(return_value=[])
    )
    monkeypatch.setattr(
        mcp_marketplace.registry_client,
        "fetch_official_mcp_registry",
        AsyncMock(return_value=[]),
    )


@pytest.mark.asyncio
async def test_list_registry_returns_all_connectors(_no_remote_registry):
    """Sem registry remoto, list_registry cai 100% pro fallback local."""
    result = await list_registry()
    assert len(result) == len(_REGISTRY)


@pytest.mark.asyncio
async def test_list_registry_items_are_mcp_connectors(_no_remote_registry):
    """list_registry deve retornar instâncias de MCPConnector."""
    result = await list_registry()
    assert all(isinstance(c, MCPConnector) for c in result)


@pytest.mark.asyncio
async def test_list_registry_prefers_remote_entry_over_local_when_id_matches(
    monkeypatch, _no_remote_registry
):
    from unittest.mock import AsyncMock

    from backend.api.handlers import mcp_marketplace

    monkeypatch.setattr(
        mcp_marketplace.registry_client,
        "fetch_catalog",
        AsyncMock(
            return_value=[
                {
                    "id": "filesystem",
                    "name": "Filesystem (remoto)",
                    "description": "d",
                    "install_cmd": "npx x",
                    "env_vars": "[]",
                    "homepage": "",
                    "category": "filesystem",
                }
            ]
        ),
    )

    result = await list_registry()

    fs = next(c for c in result if c.id == "filesystem")
    assert fs.name == "Filesystem (remoto)"
    # Demais conectores do fallback local continuam presentes, sem duplicar.
    assert len(result) == len(_REGISTRY)


@pytest.mark.asyncio
async def test_list_registry_ignores_malformed_remote_entry(
    monkeypatch, _no_remote_registry
):
    from unittest.mock import AsyncMock

    from backend.api.handlers import mcp_marketplace

    monkeypatch.setattr(
        mcp_marketplace.registry_client,
        "fetch_catalog",
        AsyncMock(return_value=[{"name": "sem id"}]),
    )

    result = await list_registry()

    assert len(result) == len(_REGISTRY)


@pytest.mark.asyncio
async def test_list_registry_merges_official_mcp_registry_entries(
    monkeypatch, _no_remote_registry
):
    """Cobre o fix pedido ao vivo: a Library mostrava só os 6 conectores
    hardcoded — agora entram também as entradas do registry oficial de MCP
    (registry.modelcontextprotocol.io), mescladas sem duplicar id."""
    from unittest.mock import AsyncMock

    from backend.api.handlers import mcp_marketplace

    monkeypatch.setattr(
        mcp_marketplace.registry_client,
        "fetch_official_mcp_registry",
        AsyncMock(
            return_value=[
                {
                    "id": "com.example/foo",
                    "name": "Foo",
                    "description": "d",
                    "install_cmd": "npx -y foo-mcp",
                    "env_vars": [],
                    "homepage": "https://github.com/example/foo",
                    "category": "community",
                }
            ]
        ),
    )

    result = await list_registry()

    assert len(result) == len(_REGISTRY) + 1
    assert any(c.id == "com.example/foo" for c in result)


@pytest.mark.asyncio
async def test_list_registry_orders_verified_first_then_alphabetical(
    monkeypatch, _no_remote_registry
):
    """Sem métrica real de popularidade na fonte, a ordenação é: conectores
    curados (`vectora_verified`) primeiro, resto em ordem alfabética por
    nome — nunca inventa relevância que a fonte não tem."""
    from unittest.mock import AsyncMock

    from backend.api.handlers import mcp_marketplace

    monkeypatch.setattr(
        mcp_marketplace.registry_client,
        "fetch_official_mcp_registry",
        AsyncMock(
            return_value=[
                {
                    "id": "zzz-unverified",
                    "name": "Zzz Unverified",
                    "description": "d",
                    "category": "community",
                },
                {
                    "id": "aaa-unverified",
                    "name": "Aaa Unverified",
                    "description": "d",
                    "category": "community",
                },
            ]
        ),
    )

    result = await list_registry()

    verified_names = [c.name for c in result if c.vectora_verified]
    unverified_names = [c.name for c in result if not c.vectora_verified]
    assert verified_names == sorted(verified_names, key=str.lower)
    assert unverified_names == ["Aaa Unverified", "Zzz Unverified"]
    # Todos os verificados vêm antes de todos os não-verificados.
    assert result.index(next(c for c in result if c.vectora_verified)) == 0
    first_unverified_idx = next(
        i for i, c in enumerate(result) if not c.vectora_verified
    )
    assert all(c.vectora_verified for c in result[:first_unverified_idx])


@pytest.mark.asyncio
async def test_list_registry_no_real_source_has_no_verified_entries_still_sorts(
    monkeypatch, _no_remote_registry
):
    """Erro/borda: lista só com entradas do registry externo (sem nenhum
    verificado) ainda ordena alfabeticamente, não quebra."""
    from unittest.mock import AsyncMock

    from backend.api.handlers import mcp_marketplace

    monkeypatch.setattr(mcp_marketplace, "_REGISTRY", [])
    monkeypatch.setattr(
        mcp_marketplace.registry_client,
        "fetch_official_mcp_registry",
        AsyncMock(
            return_value=[
                {"id": "b", "name": "Bbb", "description": "d"},
                {"id": "a", "name": "Aaa", "description": "d"},
            ]
        ),
    )

    result = await list_registry()

    assert [c.name for c in result] == ["Aaa", "Bbb"]
    assert all(not c.vectora_verified for c in result)


@pytest.mark.asyncio
async def test_list_registry_fetches_remote_and_official_in_parallel(
    monkeypatch, _no_remote_registry
):
    """Regressão de performance: as duas fontes remotas são buscadas em
    paralelo (asyncio.gather), não sequencialmente — o tempo total fica perto
    do maior atraso individual, não da soma dos dois."""
    import asyncio
    import time

    from backend.api.handlers import mcp_marketplace

    async def _slow_catalog(kind):
        await asyncio.sleep(0.1)
        return []

    async def _slow_official():
        await asyncio.sleep(0.1)
        return []

    monkeypatch.setattr(mcp_marketplace.registry_client, "fetch_catalog", _slow_catalog)
    monkeypatch.setattr(
        mcp_marketplace.registry_client, "fetch_official_mcp_registry", _slow_official
    )

    start = time.monotonic()
    await list_registry()
    elapsed = time.monotonic() - start

    assert elapsed < 0.18


@pytest.mark.asyncio
async def test_install_mcp_resolves_connector_from_remote_or_official_registry(
    _functional_store, monkeypatch
):
    """Fecha o gap encontrado: install_mcp só buscava em _REGISTRY (os 6
    hardcoded) — agora resolve qualquer conector visível em list_registry(),
    incluindo entradas do registry oficial de MCP."""
    from unittest.mock import AsyncMock

    from backend.api.handlers import mcp_marketplace

    monkeypatch.setattr(
        mcp_marketplace.registry_client,
        "fetch_official_mcp_registry",
        AsyncMock(
            return_value=[
                {
                    "id": "com.example/foo",
                    "name": "Foo",
                    "description": "d",
                    "install_cmd": "npx -y foo-mcp",
                    "env_vars": [],
                    "homepage": "",
                    "category": "community",
                }
            ]
        ),
    )

    result = await install_mcp(InstallRequest(mcp_id="com.example/foo"))

    assert result["status"] == "installed"
    servers = _functional_store.list_servers("local")
    assert any(s.name == "com.example/foo" for s in servers)


@pytest.fixture
def _functional_store(tmp_path, monkeypatch, _no_remote_registry):
    """Aponta o store MCP funcional (plugins) para um dir temporário isolado.

    Também isola dos registries remotos (`_no_remote_registry`) — `install_mcp`
    resolve o conector via `list_registry()`, que sem isso tocaria rede real
    nesses testes unitários.
    """
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

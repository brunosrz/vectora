"""Tests for Vectora MCP Server resources.

Verifica os recursos MCP (vectora://status, vectora://collections, etc.)
sem depender de APIs externas ou do Gemini CLI.

Os recursos são testados via importação direta do módulo do servidor,
não via protocolo JSON-RPC, para máxima velocidade e confiabilidade em CI.

Executar:
    uv run pytest tests/e2e/test_mcp_resources.py -v
"""

from __future__ import annotations

import json

import pytest

pytestmark = [pytest.mark.e2e, pytest.mark.timeout(30)]


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture(scope="module")
def mcp_server():
    """Importa e retorna o módulo do servidor MCP."""
    from vectora.mcp import server

    return server


@pytest.fixture(scope="module")
def mcp_instance(mcp_server):
    """Retorna a instância FastMCP registrada."""
    return mcp_server.mcp


# ============================================================================
# Testes de importação e estrutura
# ============================================================================


class TestMcpServerImport:
    """Verifica que o módulo do servidor MCP importa sem erros."""

    def test_server_module_imports(self, mcp_server):
        """O módulo vectora.mcp.server deve importar corretamente."""
        assert mcp_server is not None

    def test_mcp_instance_exists(self, mcp_instance):
        """A instância FastMCP deve estar disponível."""
        assert mcp_instance is not None

    def test_mcp_has_correct_name(self, mcp_instance):
        """O servidor MCP deve ter o nome 'Vectora'."""
        assert mcp_instance.name == "Vectora"

    def test_tool_timeouts_defined(self, mcp_server):
        """TOOL_TIMEOUTS deve estar definido com timeouts para todas as ferramentas."""
        timeouts = mcp_server.TOOL_TIMEOUTS
        assert isinstance(timeouts, dict)
        assert len(timeouts) >= 10

        expected_tools = [
            "web_search",
            "fetch_url",
            "vector_search",
            "embedding",
            "file_read",
            "file_edit",
            "file_write",
            "grep",
            "list_dir",
            "terminal",
        ]
        for tool in expected_tools:
            assert tool in timeouts, f"Timeout não definido para '{tool}'"
            assert timeouts[tool] > 0, f"Timeout de '{tool}' deve ser positivo"

    def test_with_timeout_function_exists(self, mcp_server):
        """A função _with_timeout deve existir no módulo."""
        assert hasattr(mcp_server, "_with_timeout")
        assert callable(mcp_server._with_timeout)


# ============================================================================
# Testes dos recursos MCP
# ============================================================================


class TestMcpStatusResource:
    """Testa o recurso vectora://status."""

    @pytest.mark.asyncio
    async def test_get_server_status_returns_json(self, mcp_server):
        """get_server_status() deve retornar JSON válido."""
        result = await mcp_server.get_server_status()
        data = json.loads(result)
        assert isinstance(data, dict)

    @pytest.mark.asyncio
    async def test_status_has_required_fields(self, mcp_server):
        """Recurso de status deve ter campos obrigatórios."""
        result = await mcp_server.get_server_status()
        data = json.loads(result)

        assert data["server"] == "Vectora"
        assert data["status"] == "ready"
        assert "version" in data
        assert "timestamp" in data
        assert "capabilities" in data
        assert "tools_count" in data

    @pytest.mark.asyncio
    async def test_status_tools_count_matches(self, mcp_server):
        """tools_count deve ser 13."""
        result = await mcp_server.get_server_status()
        data = json.loads(result)
        assert data["tools_count"] == 13

    @pytest.mark.asyncio
    async def test_status_capabilities_are_booleans(self, mcp_server):
        """Todas as capacidades reportadas devem ser booleanos."""
        result = await mcp_server.get_server_status()
        data = json.loads(result)
        caps = data["capabilities"]

        assert isinstance(caps, dict)
        for key, val in caps.items():
            assert isinstance(val, bool), f"capabilities[{key!r}] deve ser bool"


class TestMcpCollectionsResource:
    """Testa o recurso vectora://collections."""

    @pytest.mark.asyncio
    async def test_collections_resource_returns_json(self, mcp_server):
        """list_vector_collections() deve retornar JSON válido mesmo sem LanceDB configurado."""
        result = await mcp_server.list_vector_collections()
        # Deve ser parseable como JSON
        data = json.loads(result)
        assert isinstance(data, dict)

    @pytest.mark.asyncio
    async def test_collections_resource_does_not_raise(self, mcp_server):
        """list_vector_collections() nunca deve lançar exceção."""
        try:
            result = await mcp_server.list_vector_collections()
            assert isinstance(result, str)
        except Exception as exc:
            pytest.fail(f"list_vector_collections lançou exceção inesperada: {exc}")

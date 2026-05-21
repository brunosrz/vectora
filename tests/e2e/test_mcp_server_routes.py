"""Tests for Vectora MCP Server tool routes.

Verifica que as 13 ferramentas MCP estão registradas corretamente
e respondem a inputs inválidos com mensagens de erro, sem travar.

Não requer APIs externas — testa estrutura e comportamento defensivo
(timeouts, tratamento de erros, retorno de strings).

Executar:
    uv run pytest tests/e2e/test_mcp_server_routes.py -v
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.e2e, pytest.mark.timeout(30)]

# Nomes canônicos das 13 ferramentas expostas pelo servidor MCP
EXPECTED_TOOL_NAMES = {
    "web_search_tool",
    "fetch_url_tool",
    "vector_search_tool",
    "embedding_tool",
    "ingest_docs_tool",
    "file_read_tool",
    "file_write_tool",
    "file_edit_tool",
    "grep_tool",
    "list_dir_tool",
    "terminal_tool",
    "call_mcp_tool_tool",
    "delegate_task_to_vectora",
}


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture(scope="module")
def server():
    """Importa e retorna o módulo do servidor MCP."""
    from vectora.mcp import server as _server

    return _server


@pytest.fixture(scope="module")
def mcp(server):
    """Retorna a instância FastMCP."""
    return server.mcp


# ============================================================================
# Testes de registro de ferramentas
# ============================================================================


class TestToolRegistration:
    """Verifica que todas as 13 ferramentas estão registradas no servidor."""

    def test_exactly_13_tools_registered(self, mcp):
        """O servidor MCP deve expor exatamente 13 ferramentas."""
        tools = mcp._tool_manager.list_tools()
        assert len(tools) == 13, (
            f"Esperado 13 ferramentas, encontrado {len(tools)}: "
            f"{[t.name for t in tools]}"
        )

    def test_all_expected_tool_names_present(self, mcp):
        """Todos os nomes de ferramentas esperados devem estar registrados."""
        tools = mcp._tool_manager.list_tools()
        registered = {t.name for t in tools}
        missing = EXPECTED_TOOL_NAMES - registered
        assert not missing, f"Ferramentas ausentes: {missing}"

    def test_no_unexpected_tools(self, mcp):
        """Não deve haver ferramentas extras não documentadas."""
        tools = mcp._tool_manager.list_tools()
        registered = {t.name for t in tools}
        extra = registered - EXPECTED_TOOL_NAMES
        assert not extra, f"Ferramentas extras não esperadas: {extra}"

    def test_all_tools_have_descriptions(self, mcp):
        """Todas as ferramentas devem ter docstring/descrição não-vazia."""
        tools = mcp._tool_manager.list_tools()
        for tool in tools:
            assert tool.description, f"Ferramenta '{tool.name}' não tem descrição"


# ============================================================================
# Testes de comportamento defensivo das ferramentas
# ============================================================================


class TestToolDefensiveBehavior:
    """Verifica que ferramentas retornam strings de erro em vez de exceções."""

    @pytest.mark.asyncio
    @pytest.mark.timeout(15)
    async def test_vector_search_empty_collection_returns_string(self, server):
        """vector_search_tool com coleção inexistente deve retornar string de erro."""
        result = await server.vector_search_tool(
            query="test query",
            collection="_nonexistent_e2e_test_collection_xyz",
            limit=1,
        )
        assert isinstance(result, str), "vector_search_tool deve retornar string"
        assert len(result) > 0, "Resultado não deve ser vazio"

    @pytest.mark.asyncio
    @pytest.mark.timeout(15)
    async def test_file_read_nonexistent_returns_error_string(self, server):
        """file_read_tool com arquivo inexistente deve retornar string de erro."""
        result = await server.file_read_tool(
            path="/nonexistent/path/file_xyz_e2e_test.txt"
        )
        assert isinstance(result, str), "file_read_tool deve retornar string"
        assert len(result) > 0

    @pytest.mark.asyncio
    @pytest.mark.timeout(15)
    async def test_list_dir_nonexistent_returns_error_string(self, server):
        """list_dir_tool com diretório inexistente deve retornar string de erro."""
        result = await server.list_dir_tool(path="/nonexistent/dir/xyz_e2e_test_12345")
        assert isinstance(result, str), "list_dir_tool deve retornar string"
        assert len(result) > 0

    @pytest.mark.asyncio
    @pytest.mark.timeout(15)
    async def test_fetch_url_invalid_scheme_returns_error_string(self, server):
        """fetch_url_tool com URL inválida deve retornar string de erro."""
        result = await server.fetch_url_tool(url="not-a-valid-url")
        assert isinstance(result, str), "fetch_url_tool deve retornar string"
        assert len(result) > 0


# ============================================================================
# Testes de configuração de timeouts
# ============================================================================


class TestToolTimeouts:
    """Verifica que os timeouts estão configurados corretamente."""

    def test_all_tools_have_timeout_configured(self, server):
        """Cada ferramenta deve ter timeout definido em TOOL_TIMEOUTS."""
        timeouts = server.TOOL_TIMEOUTS

        # Nomes de ferramenta sem o sufixo "_tool" (como são indexados em TOOL_TIMEOUTS)
        expected_timeout_keys = [
            "web_search",
            "fetch_url",
            "vector_search",
            "embedding",
            "ingest_docs",
            "file_read",
            "file_edit",
            "file_write",
            "grep",
            "list_dir",
            "terminal",
            "call_mcp_tool",
        ]
        for key in expected_timeout_keys:
            assert key in timeouts, f"Timeout ausente para '{key}'"

    def test_timeouts_are_positive_floats(self, server):
        """Todos os timeouts devem ser floats positivos."""
        for key, val in server.TOOL_TIMEOUTS.items():
            assert isinstance(val, float | int), f"Timeout[{key!r}] não é numérico"
            assert val > 0, f"Timeout[{key!r}] = {val} não é positivo"

    def test_long_running_tools_have_generous_timeouts(self, server):
        """Ferramentas de operação longa devem ter timeout >= 30s."""
        timeouts = server.TOOL_TIMEOUTS
        long_running = ["embedding", "ingest_docs", "terminal"]
        for tool in long_running:
            if tool in timeouts:
                assert timeouts[tool] >= 30, (
                    f"'{tool}' deveria ter timeout >= 30s, tem {timeouts[tool]}s"
                )

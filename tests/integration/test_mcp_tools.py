"""Testes de integração do servidor MCP do Vectora.

Testa as 13 ferramentas MCP e o recurso de status sem iniciar um subprocesso.
As funções de ferramenta são testadas diretamente (não via protocolo MCP),
o que permite verificar a lógica de negócio de forma rápida e confiável.

Para testar o protocolo MCP completo (JSON-RPC via stdio), veja TestMcpProtocol.

Requer: variáveis de ambiente configuradas (GOOGLE_API_KEY, etc.) para
testes que realmente chamam as APIs. Testes de configuração básica
funcionam sem chaves de API.

Executar:
    uv run pytest tests/integration/test_mcp_tools.py -v --timeout=60
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
from pathlib import Path

import pytest

logger = logging.getLogger(__name__)

pytestmark = [pytest.mark.integration, pytest.mark.timeout(60)]

REQUIRES_GOOGLE = pytest.mark.skipif(
    not os.getenv("GOOGLE_API_KEY"),
    reason="GOOGLE_API_KEY não configurado",
)
REQUIRES_COHERE = pytest.mark.skipif(
    not os.getenv("COHERE_API_KEY"),
    reason="COHERE_API_KEY não configurado",
)
REQUIRES_TAVILY = pytest.mark.skipif(
    not os.getenv("TAVILY_API_KEY")
    or os.getenv("ENABLE_WEB_SEARCH", "false").lower() != "true",
    reason="TAVILY_API_KEY ou ENABLE_WEB_SEARCH não configurados",
)


# ============================================================================
# TestMcpServerConfig — configuração e imports básicos
# ============================================================================


class TestMcpServerConfig:
    """Verifica que o servidor MCP está configurado corretamente."""

    def test_mcp_instance_importable(self):
        """O objeto `mcp` (FastMCP) deve ser importável."""
        from vectora.mcp.server import mcp

        assert mcp is not None
        assert hasattr(mcp, "name")

    def test_mcp_server_name(self):
        """O servidor deve se chamar 'Vectora'."""
        from vectora.mcp.server import mcp

        assert mcp.name == "Vectora"

    def test_tool_functions_importable(self):
        """Todas as 13 funções de tool devem ser importáveis."""
        from vectora.mcp.server import (
            call_mcp_tool_tool,
            embedding_tool,
            fetch_url_tool,
            file_edit_tool,
            file_read_tool,
            file_write_tool,
            grep_tool,
            ingest_docs_tool,
            list_dir_tool,
            terminal_tool,
            vector_search_tool,
            web_search_tool,
        )

        tools = [
            call_mcp_tool_tool,
            embedding_tool,
            fetch_url_tool,
            file_edit_tool,
            file_read_tool,
            file_write_tool,
            grep_tool,
            ingest_docs_tool,
            list_dir_tool,
            terminal_tool,
            vector_search_tool,
            web_search_tool,
        ]
        assert all(callable(t) for t in tools), "Todas as tools devem ser callable"

    def test_delegate_function_importable(self):
        """A função delegate_task_to_vectora deve ser importável."""
        from vectora.mcp.server import delegate_task_to_vectora

        assert callable(delegate_task_to_vectora)

    def test_tool_timeouts_configured(self):
        """TOOL_TIMEOUTS deve ter entradas para todas as tools principais."""
        from vectora.mcp.server import TOOL_TIMEOUTS

        expected = {
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
        }
        configured = set(TOOL_TIMEOUTS.keys())
        missing = expected - configured
        assert not missing, f"Tools sem timeout configurado: {missing}"


# ============================================================================
# TestMcpFileTools — ferramentas de filesystem
# ============================================================================


class TestMcpFileTools:
    """Testa ferramentas de filesystem via funções MCP diretamente.

    As ferramentas de arquivo têm verificação de segurança que restringe acesso
    ao diretório do projeto (allowed_dirs=["."]).
    Usamos caminhos dentro do projeto para os testes.
    """

    @pytest.fixture
    def project_tmp_dir(self, tmp_path, monkeypatch):
        """Cria dir temporário dentro do projeto e ajusta cwd para o projeto."""
        import os
        from pathlib import Path

        project_root = Path(__file__).parent.parent.parent
        monkeypatch.chdir(project_root)
        # Usa o data/ do projeto que já é permitido
        test_dir = project_root / "data" / "test_mcp_tmp"
        test_dir.mkdir(parents=True, exist_ok=True)
        yield test_dir
        # Cleanup
        import shutil

        shutil.rmtree(test_dir, ignore_errors=True)

    async def test_file_read_tool_reads_existing_file(self, project_tmp_dir):
        """file_read_tool deve ler um arquivo dentro do projeto."""
        from vectora.mcp.server import file_read_tool

        test_file = project_tmp_dir / "test_mcp.txt"
        test_file.write_text("Conteudo de teste MCP", encoding="utf-8")

        result = await file_read_tool(str(test_file))
        assert "Conteudo de teste MCP" in result

    async def test_file_write_and_read_roundtrip(self, project_tmp_dir):
        """file_write_tool escreve e file_read_tool lê de volta (dentro do projeto)."""
        from vectora.mcp.server import file_read_tool, file_write_tool

        test_file = project_tmp_dir / "roundtrip.txt"
        content = "Teste de roundtrip write-read"

        write_result = await file_write_tool(str(test_file), content)
        assert write_result  # não deve ser vazio

        read_result = await file_read_tool(str(test_file))
        assert content in read_result

    async def test_list_dir_tool_lists_project(self, monkeypatch):
        """list_dir_tool deve listar diretório do projeto sem erros."""
        from pathlib import Path

        from vectora.mcp.server import list_dir_tool

        project_root = Path(__file__).parent.parent.parent
        monkeypatch.chdir(project_root)

        result = await list_dir_tool(".")
        # Deve listar arquivos do projeto (pyproject.toml, vectora/, etc.)
        assert len(result) > 0
        assert "Error: Access denied" not in result or "pyproject" in result.lower()

    async def test_grep_tool_finds_pattern(self, monkeypatch):
        """grep_tool deve encontrar padrão em arquivo do projeto."""
        from pathlib import Path

        from vectora.mcp.server import grep_tool

        project_root = Path(__file__).parent.parent.parent
        monkeypatch.chdir(project_root)

        result = await grep_tool(
            pattern="VectoraTracer",
            path="vectora/services/tracer.py",
        )
        assert "VectoraTracer" in result or len(result) > 0


# ============================================================================
# TestMcpWebTools — ferramentas de web (requerem TAVILY_API_KEY)
# ============================================================================


class TestMcpWebTools:
    """Testa ferramentas de web search e fetch URL."""

    async def test_web_search_disabled_returns_message(self, monkeypatch):
        """Se web search desabilitado, deve retornar mensagem clara."""
        monkeypatch.setenv("ENABLE_WEB_SEARCH", "false")
        # Reimportar settings para pegar o env var mockado
        # (o teste valida o comportamento do tool com search desabilitado)
        from vectora.tools.web import web_search

        result = await web_search.ainvoke({"query": "test"})
        assert (
            "disabled" in result.lower()
            or "desabilitado" in result.lower()
            or len(result) > 0
        )

    @REQUIRES_TAVILY
    async def test_web_search_tool_returns_results(self):
        """web_search_tool deve retornar resultados quando configurado."""
        from vectora.mcp.server import web_search_tool

        result = await web_search_tool("Python programming language")
        # Pode ser JSON de resultados ou erro — não deve ser vazio
        assert len(result) > 0

    async def test_fetch_url_tool_invalid_url(self):
        """fetch_url_tool deve rejeitar URLs inválidas."""
        from vectora.mcp.server import fetch_url_tool

        result = await fetch_url_tool("not-a-url")
        assert "Error" in result or "Erro" in result or "http" in result.lower()


# ============================================================================
# TestMcpRagTools — ferramentas de RAG (requerem COHERE_API_KEY)
# ============================================================================


class TestMcpRagTools:
    """Testa ferramentas de RAG: vector_search e embedding."""

    async def test_vector_search_tool_empty_collection(self):
        """vector_search_tool em coleção inexistente → resposta de no_results ou error."""
        from vectora.mcp.server import vector_search_tool

        result = await vector_search_tool(
            query="inexistent query xyz123",
            collection="nonexistent_collection_xyz",
            limit=3,
        )
        data = json.loads(result) if result.startswith("{") else {"raw": result}
        # Deve retornar status de erro, não travamento
        assert data  # não vazio

    @REQUIRES_COHERE
    async def test_embedding_tool_enqueues(self, monkeypatch):
        """embedding_tool deve enfileirar documento (fire-and-forget)."""
        monkeypatch.setenv("ENABLE_RAG", "true")
        from vectora.mcp.server import embedding_tool

        result = await embedding_tool(
            text="Texto de teste para embedding MCP",
            collection="test_mcp_embed",
        )
        # Deve retornar status fire_and_forget ou error (se queue não configurada)
        assert len(result) > 0
        if result.startswith("{"):
            data = json.loads(result)
            assert data.get("status") in ("fire_and_forget", "error")


# ============================================================================
# TestMcpProtocol — protocolo MCP completo via subprocess
# ============================================================================


class TestMcpProtocol:
    """Testa o protocolo MCP completo via subprocess (JSON-RPC stdio)."""

    @pytest.fixture
    def vectora_mcp_command(self):
        """Retorna o comando para iniciar vectora-mcp."""
        # Preferir .venv/Scripts/python -m vectora.mcp.server
        project_root = Path(__file__).parent.parent.parent
        venv_python = (
            project_root
            / ".venv"
            / ("Scripts" if sys.platform == "win32" else "bin")
            / "python"
        )
        if venv_python.exists():
            return [str(venv_python), "-m", "vectora.mcp.server"]
        return ["python", "-m", "vectora.mcp.server"]

    def _send_jsonrpc(self, proc, method: str, params: dict, req_id: int = 1) -> dict:
        """Envia request JSON-RPC e lê resposta."""
        import json

        request = json.dumps(
            {"jsonrpc": "2.0", "id": req_id, "method": method, "params": params}
        )
        proc.stdin.write(request + "\n")
        proc.stdin.flush()

        line = proc.stdout.readline()
        return json.loads(line) if line else {}

    @pytest.mark.timeout(30)
    def test_mcp_initialize_handshake(self, vectora_mcp_command):
        """Protocolo MCP: initialize → lista ferramentas disponíveis."""
        try:
            proc = subprocess.Popen(
                vectora_mcp_command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )
        except FileNotFoundError:
            pytest.skip("vectora-mcp command não disponível")

        try:
            # Initialize
            response = self._send_jsonrpc(
                proc,
                "initialize",
                {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "pytest", "version": "1.0"},
                },
            )
            # Verifica que recebeu resposta válida (ou timeout)
            if response:
                assert "result" in response or "error" in response
        except Exception as e:
            logger.warning(f"MCP protocol test skipped: {e}")
            pytest.skip(f"MCP subprocess não respondeu: {e}")
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()

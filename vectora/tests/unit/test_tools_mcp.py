"""Testes para backend/tools/mcp.py — client MCP nativo (SDK oficial `mcp`,
sem langchain-mcp-adapters). Servidor real via stdio (tests/fixtures/
dummy_mcp_server.py), não mock de protocolo.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from backend.tools import mcp as mcp_tool_module
from backend.tools.mcp import VectoraMCPClient, _safe_subprocess_env, call_mcp_tool

_DUMMY_SERVER = str(
    Path(__file__).resolve().parent.parent / "fixtures" / "dummy_mcp_server.py"
)
_DUMMY_SERVER_CRASHES = str(
    Path(__file__).resolve().parent.parent / "fixtures" / "dummy_mcp_server_crashes.py"
)


@pytest.fixture(autouse=True)
def _reset_global_client(monkeypatch):
    """Cada teste começa sem client global cacheado — evita vazamento de
    estado entre testes (o módulo usa um singleton lazy)."""
    monkeypatch.setattr(mcp_tool_module, "_mcp_client", None)
    yield
    monkeypatch.setattr(mcp_tool_module, "_mcp_client", None)


@pytest.fixture
def _enable_mcp(monkeypatch):
    monkeypatch.setattr(mcp_tool_module.settings, "enable_mcp", True)


@pytest.fixture
def _dummy_server_settings(monkeypatch):
    monkeypatch.setattr(mcp_tool_module.settings, "mcp_command", sys.executable)
    monkeypatch.setattr(mcp_tool_module.settings, "mcp_command_args", [_DUMMY_SERVER])
    monkeypatch.setattr(mcp_tool_module.settings, "mcp_server_url", None)


class TestSafeSubprocessEnv:
    def test_allowlist_nunca_inclui_chave_sensivel(self, monkeypatch):
        monkeypatch.setenv("VECTORA_ANTHROPIC_API_KEY", "sk-segredo")
        monkeypatch.setenv("PATH", "/usr/bin")
        env = _safe_subprocess_env()
        assert "VECTORA_ANTHROPIC_API_KEY" not in env
        assert "PATH" in env


class TestVectoraMCPClientReal:
    """Conecta de verdade num subprocesso stdio (dummy_mcp_server.py)."""

    async def test_conecta_lista_tools_e_chama_tool_com_sucesso(self):
        client = VectoraMCPClient()
        try:
            await client.connect(
                {
                    "dummy": {
                        "transport": "stdio",
                        "command": sys.executable,
                        "args": [_DUMMY_SERVER],
                    }
                }
            )
            tools = client.tools()
            assert "echo" in tools
            assert "sum_numbers" in tools

            result = await client.call_tool("echo", {"text": "ola"})
            assert result == "echo: ola"

            result_sum = await client.call_tool("sum_numbers", {"a": 2, "b": 3})
            assert result_sum == "5"
        finally:
            await client.aclose()

    async def test_env_do_subprocesso_e_allowlist_nao_variavel_sensivel(
        self, monkeypatch
    ):
        monkeypatch.setenv("VECTORA_SEGREDO_DE_TESTE", "nao-deveria-vazar")
        client = VectoraMCPClient()
        try:
            await client.connect(
                {
                    "dummy": {
                        "transport": "stdio",
                        "command": sys.executable,
                        "args": [_DUMMY_SERVER],
                    }
                }
            )
            result = await client.call_tool(
                "read_env_var", {"name": "VECTORA_SEGREDO_DE_TESTE"}
            )
            assert result == "ausente"
        finally:
            await client.aclose()

    async def test_servidor_que_cai_no_handshake_nao_quebra_connect(self):
        """Um servidor configurado que falha ao iniciar não deve impedir
        outros servidores (aqui, só ele mesmo) — connect() nunca propaga."""
        client = VectoraMCPClient()
        try:
            await client.connect(
                {
                    "quebrado": {
                        "transport": "stdio",
                        "command": sys.executable,
                        "args": [_DUMMY_SERVER_CRASHES],
                    }
                }
            )
            assert client.tools() == {}
        finally:
            await client.aclose()

    async def test_tool_desconhecida_levanta_keyerror(self):
        client = VectoraMCPClient()
        try:
            await client.connect(
                {
                    "dummy": {
                        "transport": "stdio",
                        "command": sys.executable,
                        "args": [_DUMMY_SERVER],
                    }
                }
            )
            with pytest.raises(KeyError):
                await client.call_tool("tool_que_nao_existe", {})
        finally:
            await client.aclose()

    async def test_transporte_desconhecido_nao_derruba_connect(self):
        """`connect()` captura falha por servidor (inclui transporte
        desconhecido) — nunca propaga, o cliente segue usável sem essa
        conexão específica."""
        client = VectoraMCPClient()
        try:
            await client.connect({"x": {"transport": "carrier-pigeon"}})
            assert client.tools() == {}
        finally:
            await client.aclose()


class TestCallMcpToolIntegration:
    """Fluxo ponta a ponta da tool exposta ao agente."""

    async def test_mcp_desabilitado_retorna_aviso(self, monkeypatch):
        monkeypatch.setattr(mcp_tool_module.settings, "enable_mcp", False)
        result = await call_mcp_tool.ainvoke({"tool_name": "echo", "arguments": "{}"})
        assert "desabilitado" in result.lower()

    async def test_arguments_json_invalido_retorna_erro_tipado(self, _enable_mcp):
        result = await call_mcp_tool.ainvoke(
            {"tool_name": "echo", "arguments": "{invalido"}
        )
        assert "JSON válido" in result

    async def test_nenhum_servidor_configurado_retorna_aviso(
        self, _enable_mcp, monkeypatch
    ):
        monkeypatch.setattr(mcp_tool_module.settings, "mcp_server_url", None)
        monkeypatch.setattr(mcp_tool_module.settings, "mcp_command", None)
        result = await call_mcp_tool.ainvoke({"tool_name": "echo", "arguments": "{}"})
        assert "Nenhuma tool MCP disponível" in result

    async def test_happy_path_chama_tool_do_servidor_real(
        self, _enable_mcp, _dummy_server_settings
    ):
        result = await call_mcp_tool.ainvoke(
            {"tool_name": "echo", "arguments": '{"text": "mundo"}'}
        )
        assert result == "echo: mundo"

    async def test_tool_inexistente_lista_disponiveis(
        self, _enable_mcp, _dummy_server_settings
    ):
        result = await call_mcp_tool.ainvoke(
            {"tool_name": "nao_existe", "arguments": "{}"}
        )
        assert "não encontrada" in result
        assert "echo" in result

    async def test_timeout_retorna_erro_tipado(
        self, _enable_mcp, _dummy_server_settings, monkeypatch
    ):
        monkeypatch.setattr(mcp_tool_module.settings, "mcp_timeout", 0)
        result = await call_mcp_tool.ainvoke(
            {"tool_name": "echo", "arguments": '{"text": "x"}'}
        )
        assert "excedeu" in result

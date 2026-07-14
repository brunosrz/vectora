"""MCPClient contra um servidor MCP stdio real (sem mock de stdio_client).

Diferente dos testes existentes de client.py (mock total do transporte),
este arquivo spawna de verdade `tests/fixtures/dummy_mcp_server.py` como
subprocesso e valida o protocolo JSON-RPC real sobre pipes reais.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from backend.mcp.client import MCPClient

_FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"
_DUMMY_SERVER = _FIXTURES_DIR / "dummy_mcp_server.py"
_DUMMY_SERVER_CRASHES = _FIXTURES_DIR / "dummy_mcp_server_crashes.py"


@pytest.mark.asyncio
async def test_mcp_client_conecta_e_inicializa_sessao_real():
    client = MCPClient(command=sys.executable, args=[str(_DUMMY_SERVER)])

    async with client:
        assert client.session is not None
        tools = await client.list_tools()
        tool_names = {t.name for t in tools}
        assert "echo" in tool_names

    # Par de erro no mesmo teste: fora do "async with", a sessão foi
    # realmente fechada — não é só um objeto zerado por fora.
    assert client.session is None


@pytest.mark.asyncio
async def test_mcp_client_chama_tool_echo_via_sessao_real():
    client = MCPClient(command=sys.executable, args=[str(_DUMMY_SERVER)])

    async with client:
        result = await client.call_tool("echo", {"text": "vectora"})

    assert result.is_error is False
    assert any("vectora" in item.get("text", "") for item in result.content)


@pytest.mark.asyncio
async def test_mcp_client_comando_inexistente_levanta_connection_error():
    client = MCPClient(command="este-binario-nao-existe-xyz-vectora")

    with pytest.raises(ConnectionError):
        await client.connect()


@pytest.mark.asyncio
async def test_mcp_client_servidor_que_morre_antes_de_inicializar_levanta_connection_error():
    client = MCPClient(command=sys.executable, args=[str(_DUMMY_SERVER_CRASHES)])

    with pytest.raises(ConnectionError):
        await client.connect()

"""VectoraProxy contra um servidor MCP stdio real (sem mock de stdio_client).

client.py e proxy.py implementam o mesmo padrão stdio de forma independente
(proxy.py não reusa MCPClient) — merece cobertura real própria, já que as
duas implementações podem divergir silenciosamente sem que nenhum teste
perceba (ambas só eram mockadas antes deste arquivo).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from backend.mcp.proxy import VectoraProxy, VectoraProxyError

_FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"
_DUMMY_SERVER = _FIXTURES_DIR / "dummy_mcp_server.py"
_DUMMY_SERVER_CRASHES = _FIXTURES_DIR / "dummy_mcp_server_crashes.py"


@pytest.mark.asyncio
async def test_vectora_proxy_conecta_e_lista_tools_real():
    proxy = VectoraProxy(
        transport="stdio", command=sys.executable, args=[str(_DUMMY_SERVER)]
    )

    async with proxy:
        tools = await proxy.list_tools()
        names = {t["name"] for t in tools}
        assert "echo" in names

    # Par de erro no mesmo teste: fora do "async with", desconectou de fato.
    assert proxy._session is None


@pytest.mark.asyncio
async def test_vectora_proxy_chama_tool_echo_via_sessao_real():
    proxy = VectoraProxy(
        transport="stdio", command=sys.executable, args=[str(_DUMMY_SERVER)]
    )

    async with proxy:
        result = await proxy.call_tool("echo", {"text": "vectora-proxy"})

    assert "vectora-proxy" in result


@pytest.mark.asyncio
async def test_vectora_proxy_call_tool_sem_conectar_levanta_erro_claro():
    proxy = VectoraProxy(
        transport="stdio", command=sys.executable, args=[str(_DUMMY_SERVER)]
    )

    with pytest.raises(VectoraProxyError, match="não conectado"):
        await proxy.call_tool("echo", {"text": "x"})


@pytest.mark.asyncio
async def test_vectora_proxy_comando_inexistente_levanta_proxy_error():
    proxy = VectoraProxy(
        transport="stdio", command="este-binario-nao-existe-xyz-vectora"
    )

    with pytest.raises(VectoraProxyError):
        await proxy.connect()


@pytest.mark.asyncio
async def test_vectora_proxy_servidor_que_morre_antes_de_inicializar_levanta_proxy_error():
    proxy = VectoraProxy(
        transport="stdio", command=sys.executable, args=[str(_DUMMY_SERVER_CRASHES)]
    )

    with pytest.raises(VectoraProxyError):
        await proxy.connect()

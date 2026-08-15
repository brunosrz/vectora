"""Servidor MCP stdio real (SDK oficial `mcp`) usado como fixture pelos
testes de `backend/tools/mcp.py`. Roda como subprocesso — não é mock.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

server = FastMCP("dummy-mcp-server")


@server.tool()
def echo(text: str) -> str:
    """Devolve o texto recebido, prefixado."""
    return f"echo: {text}"


@server.tool()
def sum_numbers(a: int, b: int) -> str:
    """Soma dois inteiros."""
    return str(a + b)


@server.tool()
def read_env_var(name: str) -> str:
    """Devolve o valor de uma variável de ambiente do processo servidor,
    ou 'ausente' se não estiver setada — usado pra provar o filtro de env
    do subprocess stdio (allowlist, não herança total de os.environ)."""
    import os

    return os.environ.get(name, "ausente")


if __name__ == "__main__":
    server.run(transport="stdio")

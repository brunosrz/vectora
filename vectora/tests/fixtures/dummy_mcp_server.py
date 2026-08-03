"""Servidor MCP stdio mínimo usado pelos testes reais de client.py/proxy.py.

Standalone de propósito: roda como processo filho via
`sys.executable <este arquivo>`, sem importar nada de `backend/` — não pode
depender do ambiente do processo pai além do que `mcp` já garante.

Uso nos testes:
    from pathlib import Path
    DUMMY_SERVER = Path(__file__).parent / "dummy_mcp_server.py"
    MCPClient(command=sys.executable, args=[str(DUMMY_SERVER)])
"""

from __future__ import annotations

from mcp.server.mcpserver import MCPServer

mcp = MCPServer("dummy-test-server")


@mcp.tool()
def echo(text: str) -> str:
    """Devolve o texto recebido, sem transformação."""
    return text


if __name__ == "__main__":
    mcp.run(transport="stdio")

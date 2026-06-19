"""MCP Module: Model Context Protocol integration for Vectora.

Exposes Vectora capabilities via MCP protocol:
- server.py: FastMCP server montado em ``/mcp`` (SSE) pelo FastAPI — sempre-ativo,
  sobe com todo boot do backend (sem processo nem entry point standalone)
- client.py: Internal client for consuming OTHER MCP servers (via call_mcp_tool)
- proxy.py: External client helper for agents to connect TO Vectora (multi-agent)

Usage:
    # Connect to other MCP servers from within Vectora (internal):
    from vectora.mcp.client import MCPClient

    # Connect TO Vectora from external agents (Paperclip, etc):
    from vectora.mcp.proxy import VectoraProxy, create_remote_proxy

    async with create_remote_proxy("http://vectora:8080/mcp/sse") as vectora:
        result = await vectora.delegate("task", thread_id="agent_42")
"""

from __future__ import annotations

__all__ = [
    "MCPClient",
    "VectoraProxy",
    "create_local_proxy",
    "create_remote_proxy",
]


def __getattr__(name: str) -> object:
    """Lazy imports para evitar circular import e carregamento pesado."""
    if name == "MCPClient":
        from backend.mcp.client import MCPClient

        return MCPClient
    if name in ("VectoraProxy", "create_local_proxy", "create_remote_proxy"):
        from backend.mcp import proxy as _proxy

        return getattr(_proxy, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

"""MCP Module: Model Context Protocol integration for Vectora.

Exposes Vectora capabilities via MCP protocol:
- server.py: FastMCP server (stdio + SSE transport) for Claude Desktop/Code/Paperclip
- client.py: Internal client for consuming OTHER MCP servers (via call_mcp_tool)
- proxy.py: External client helper for agents to connect TO Vectora (multi-agent)

Usage:
    # Start as MCP server (via pyproject.toml entry point):
    vectora-mcp  →  vectora.mcp.server:run

    # Connect to other MCP servers from within Vectora (internal):
    from vectora.mcp.client import MCPClient

    # Connect TO Vectora from external agents (Paperclip, etc):
    from vectora.mcp.proxy import VectoraProxy, create_remote_proxy

    async with create_remote_proxy("http://vectora:8000/sse") as vectora:
        result = await vectora.delegate("task", thread_id="agent_42")
"""

from __future__ import annotations

__all__ = [
    "MCPClient",
    "VectoraProxy",
    "create_local_proxy",
    "create_remote_proxy",
    "run",
]


def __getattr__(name: str) -> object:
    """Lazy imports para evitar circular import e carregamento pesado."""
    if name == "MCPClient":
        from vectora.mcp.client import MCPClient

        return MCPClient
    if name in ("VectoraProxy", "create_local_proxy", "create_remote_proxy"):
        from vectora.mcp import proxy as _proxy

        return getattr(_proxy, name)
    if name == "run":
        from vectora.mcp.server import run

        return run
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

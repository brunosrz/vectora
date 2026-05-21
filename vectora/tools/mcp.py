"""MCP tool: invoca ferramentas de outros servidores via Model Context Protocol."""

import asyncio
import json
import logging
from typing import Any

from langchain.tools import tool

from vectora.config.settings import settings

try:
    from langchain_mcp_adapters import MultiServerMCPClient  # type: ignore
except ImportError:
    MultiServerMCPClient = None

logger = logging.getLogger(__name__)

# Cache global — reutiliza a conexão entre chamadas
_mcp_client: Any | None = None
_mcp_tools_cache: dict[str, Any] | None = None


async def _get_mcp_client() -> Any | None:
    """Obtém ou cria instância global do cliente MCP."""
    global _mcp_client

    if _mcp_client is not None:
        return _mcp_client

    if MultiServerMCPClient is None:
        logger.warning("MultiServerMCPClient not available")
        return None

    if not settings.mcp_server_url and not settings.mcp_command:
        logger.debug("No MCP servers configured")
        return None

    try:
        servers: dict[str, Any] = {}
        if settings.mcp_server_url:
            servers["default"] = {
                "url": settings.mcp_server_url,
                "transport": settings.mcp_transport_type,
            }
        if settings.mcp_command:
            servers["local"] = {
                "command": settings.mcp_command,
                "args": settings.mcp_command_args or [],
                "transport": "stdio",
            }

        _mcp_client = MultiServerMCPClient(servers=servers)
        await _mcp_client.__aenter__()
        logger.info("MCP client initialized", extra={"servers": list(servers.keys())})
        return _mcp_client
    except Exception:
        logger.exception("Failed to initialize MCP client")
        _mcp_client = None
        return None


async def _get_mcp_tools() -> dict[str, Any] | None:
    """Obtém ferramentas MCP disponíveis do cliente inicializado."""
    global _mcp_tools_cache

    if _mcp_tools_cache is not None:
        return _mcp_tools_cache

    client = await _get_mcp_client()
    if client is None:
        return None

    try:
        tools_response = await client.list_tools()
        _mcp_tools_cache = {t.name: t for t in tools_response.tools}
        logger.info("MCP tools loaded", extra={"count": len(_mcp_tools_cache)})
        return _mcp_tools_cache
    except Exception:
        logger.exception("Failed to list MCP tools")
        _mcp_tools_cache = {}
        return _mcp_tools_cache


@tool
async def call_mcp_tool(tool_name: str, arguments: str) -> str:
    """Invoca ferramentas via MCP Protocol para integração com outros agentes.

    Args:
        tool_name: Nome da ferramenta no servidor MCP
        arguments: Argumentos em formato JSON string

    Returns:
        Resposta da ferramenta MCP
    """
    global _mcp_client

    if MultiServerMCPClient is None:
        return "MCP client not available. Install: pip install langchain-mcp-adapters"

    if not settings.enable_mcp or not settings.mcp_server_url:
        return "MCP is disabled or server URL not configured."

    try:
        if _mcp_client is None:
            _mcp_client = MultiServerMCPClient()
            if settings.mcp_transport_type == "http":
                await _mcp_client.connect_sse(settings.mcp_server_url)

        logger.info("call_mcp_tool", extra={"tool": tool_name, "arguments": arguments})

        args_dict = json.loads(arguments)

        async with asyncio.timeout(settings.mcp_timeout):
            result_text = ""
            async for event in _mcp_client.astream_events(
                {"tool_name": tool_name, "arguments": args_dict}, version="v1"
            ):
                if event.get("event") == "on_tool_stream":
                    chunk = event.get("data", {}).get("chunk")
                    if chunk:
                        result_text += str(chunk)

        return result_text or str(args_dict)

    except TimeoutError:
        logger.exception(
            f"MCP tool {tool_name} timed out after {settings.mcp_timeout}s"
        )
        return f"Error: MCP tool {tool_name} timed out."
    except Exception as e:
        logger.exception("call_mcp_tool_failed", extra={"tool": tool_name})
        return f"Error invoking MCP tool: {e!s}"

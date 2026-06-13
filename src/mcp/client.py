"""Vectora MCP Client: Consumes tools and resources from other MCP servers.

This module provides the MCPClient class, which allows Vectora to act as a
client to other MCP servers (e.g., Google Maps, Slack, GitHub).
"""

import asyncio
import contextlib
import logging
from types import TracebackType
from typing import Any, Self

from mcp.client.stdio import stdio_client
from pydantic import BaseModel, Field

from mcp import ClientSession, StdioServerParameters

logger = logging.getLogger("src.mcp.client")


class MCPToolCallResult(BaseModel):
    """Result of an MCP tool execution."""

    content: list[dict[str, Any]] = Field(default_factory=list)
    is_error: bool = False


class MCPClient:
    """Client for connecting to and interacting with MCP servers.

    This client uses the stdio transport to communicate with MCP servers
    running as subprocesses.
    """

    def __init__(
        self,
        command: str,
        args: list[str] | None = None,
        env: dict[str, str] | None = None,
    ) -> None:
        """Initialize the MCP client with server connection parameters.

        Args:
            command: The command to run the MCP server (e.g., "npx", "python").
            args: Arguments for the command.
            env: Optional environment variables for the server process.
        """
        self.server_params = StdioServerParameters(
            command=command,
            args=args or [],
            env=env,
        )
        self.session: ClientSession | None = None
        self._exit_stack = contextlib.AsyncExitStack()

    async def __aenter__(self) -> Self:
        """Context manager entry point."""
        await self.connect()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Context manager exit point."""
        await self.disconnect()

    async def connect(self) -> None:
        """Establish connection to the MCP server."""
        logger.info(
            "Connecting to MCP server: %s %s",
            self.server_params.command,
            " ".join(self.server_params.args),
        )

        try:
            # We use an ExitStack to manage the context managers properly in an async way
            read_stream, write_stream = await self._exit_stack.enter_async_context(
                stdio_client(self.server_params)
            )
            self.session = await self._exit_stack.enter_async_context(
                ClientSession(read_stream, write_stream)
            )

            # Initialize the session
            await self.session.initialize()
            logger.info("Successfully connected and initialized MCP session")

        except Exception as e:
            logger.exception("Failed to connect to MCP server")
            await self.disconnect()
            raise ConnectionError(f"Could not connect to MCP server: {e}") from e

    async def disconnect(self) -> None:
        """Close the connection to the MCP server."""
        if self.session:
            logger.info("Disconnecting from MCP server")
            self.session = None

        await self._exit_stack.aclose()
        logger.debug("MCP client disconnected and resources cleaned up")

    async def list_tools(self) -> list[Any]:
        """List available tools from the connected MCP server.

        Returns:
            A list of tool definitions.
        """
        if not self.session:
            raise RuntimeError("MCP client is not connected. Call connect() first.")

        try:
            result = await self.session.list_tools()
            return result.tools
        except Exception as e:
            logger.exception("Error listing MCP tools")
            raise RuntimeError(f"Failed to list tools: {e}") from e

    async def call_tool(
        self, name: str, arguments: dict[str, Any] | None = None
    ) -> MCPToolCallResult:
        """Call a tool on the connected MCP server.

        Args:
            name: The name of the tool to call.
            arguments: The arguments to pass to the tool.

        Returns:
            An MCPToolCallResult object containing the output and error status.
        """
        if not self.session:
            raise RuntimeError("MCP client is not connected. Call connect() first.")

        logger.info("Calling MCP tool: %s with args: %s", name, arguments)

        try:
            result = await self.session.call_tool(name, arguments or {})

            # Convert the result content to a serializable format
            # result.content items are typically TextContent, ImageContent, or EmbeddedResource
            # We convert them to dicts for easier consumption
            content_list = [item.model_dump() for item in result.content]

            return MCPToolCallResult(content=content_list, is_error=result.isError)

        except Exception as e:
            logger.exception("Error calling MCP tool: %s", name)
            return MCPToolCallResult(
                content=[{"type": "text", "text": f"Error: {e}"}], is_error=True
            )

    async def list_resources(self) -> list[Any]:
        """List available resources from the connected MCP server.

        Returns:
            A list of resource definitions.
        """
        if not self.session:
            raise RuntimeError("MCP client is not connected. Call connect() first.")

        try:
            result = await self.session.list_resources()
            return result.resources
        except Exception as e:
            logger.exception("Error listing MCP resources")
            raise RuntimeError(f"Failed to list resources: {e}") from e

    async def read_resource(self, uri: str) -> str:
        """Read a resource from the connected MCP server.

        Args:
            uri: The URI of the resource to read.

        Returns:
            The content of the resource as a string.
        """
        if not self.session:
            raise RuntimeError("MCP client is not connected. Call connect() first.")

        try:
            result = await self.session.read_resource(uri)  # ty: ignore[invalid-argument-type]
            # Typically returns a list of contents, we join them if they are text
            return "\n".join(  # ty: ignore[no-matching-overload]
                [item.text for item in result.contents if hasattr(item, "text")]
            )
        except Exception as e:
            logger.exception("Error reading MCP resource: %s", uri)
            raise RuntimeError(f"Failed to read resource {uri}: {e}") from e

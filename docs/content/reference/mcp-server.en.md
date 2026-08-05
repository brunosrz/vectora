---
title: MCP Client
weight: 5
---

Vectora consumes third-party MCP servers — it does not expose itself as an MCP server to other harnesses. Configure connectors in **Settings → Environment → Plugins**, with support for `stdio`, `sse`, and `http` transports.

## Installing a connector

The workbench **Library** tab lists a curated MCP connector marketplace (`GET /mcp/registry`) — install/uninstall right there, or register a custom MCP server manually in **Settings → Environment → Plugins**.

## How the agent uses it

The `call_mcp_tool` tool (`backend/tools/mcp.py`) delegates calls to any connected MCP server, via `MultiServerMCPClient` (`langchain_mcp_adapters`) — the agent discovers and invokes the tools exposed by the external server from within the LangGraph graph itself, subject to the same `HumanInTheLoopMiddleware`/`permission_mode` that protects any other chat tool.

See [Using settings](../../guides/using-settings) for per-workspace configuration details.

---
title: Connecting MCP Clients
weight: 5
---

Vectora exposes an **always-on** MCP server, mounted at `/mcp` in the same FastAPI process — there's no separate MCP process or dedicated port. Any MCP client (Claude Code, Claude Desktop, Cursor, Zed, or your own agent) can connect and delegate tasks to Vectora.

## Configure in Claude Desktop / Claude Code

Add this to your MCP config file:

```json
{
  "mcpServers": {
    "Vectora": {
      "url": "http://localhost:8080/mcp"
    }
  }
}
```

In production, use your server's public HTTPS URL:

```json
{
  "mcpServers": {
    "Vectora": {
      "url": "https://vectora.yourdomain.com/mcp"
    }
  }
}
```

## What gets exposed

The same native agent tools (files, git, terminal, RAG, web) become available to the external client, subject to the same ABAC policies and HITL mechanism that apply in chat.

## Adding third-party MCP servers to Vectora

Vectora is also an MCP **client** — you can connect external MCP servers and the agent starts using their tools. Configure this in **Settings → Environment → Plugins**, with support for three transports:

| Transport | Use                                      |
| --------- | ---------------------------------------- |
| `stdio`   | command + args, local process            |
| `sse`     | remote server URL via Server-Sent Events |
| `http`    | remote server URL via HTTP               |

A per-server **Tool Policy** panel lets you restrict which tools from that MCP are enabled.

## See also

- [MCP server (technical reference)](../../reference/mcp-server)
- [Using settings](../using-settings) — the Plugins tab in detail

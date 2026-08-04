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

25 native tools become available to the external client: files, read-only git, Context Graph, RAG, search, terminal, and delegation — see the full list in [MCP Server](../../reference/mcp-server).

**Writes and terminal require per-workspace approval.** Unlike chat (which goes through `HumanInTheLoopMiddleware`), an MCP client calls tools directly — without that approval, `file_write`/`file_edit`/`terminal` refuse to execute. Approve once via `POST /workspaces/approve-mcp-write` before asking the client to write files or run commands. Read-only tools work with no approval needed.

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

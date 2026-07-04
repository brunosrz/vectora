---
title: MCP Server
weight: 5
---

Vectora's MCP server is **always on**: it starts up with `vectora start`, mounted at `/mcp` in the same FastAPI process (via `FastMCP`, SSE transport) — there's no separate MCP process or dedicated port.

## Connecting

```json
{
  "mcpServers": {
    "Vectora": {
      "url": "http://localhost:8080/mcp"
    }
  }
}
```

In production, use your server's public HTTPS URL: `https://vectora.yourdomain.com/mcp`.

See the [Connecting MCP Clients](../../guides/mcp-clients) guide for full instructions.

## What gets exposed

The same native agent tools (files, git, terminal, RAG, web) — subject to the same ABAC/tool policy that applies in chat. An external client connecting via MCP doesn't get any more privilege than a user would have in the web chat.

## Vectora as an MCP client

Besides being a server, Vectora also consumes third-party MCP servers — configured in **Settings → Environment → Plugins**, with support for `stdio`, `sse`, and `http` transports. See [Using settings](../../guides/using-settings).

## Security

Every tool call via MCP goes through the same HITL and ABAC mechanism as chat — it's not a bypass channel.

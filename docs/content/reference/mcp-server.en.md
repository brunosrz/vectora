---
title: MCP Server
weight: 5
---

Vectora's MCP server is **always on**: it starts with every backend boot (`vectora start`/`vectora web`), mounted at `/mcp` in the same FastAPI process (`mcp` SDK, SSE transport) — there's no separate MCP process or dedicated port.

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

25 read and write tools: files (`file_read`/`file_edit`/`file_write`), search (`grep`, `list_dir`, `vector_search`, `web_search`, `fetch_url`), RAG (`embedding`, `ingest_docs`, `manage_retriever`), workspace (`workspace_describe`/`workspace_list`/`bucket_summary`), read-only git (`git_status`/`git_diff`/`git_log`), Context Graph (`graph_query`/`graph_explain`/`graph_path`/`graph_affected`), `terminal`, delegation (`delegate_task_to_vectora`), and metrics (`vectora_metrics`).

## Security: per-workspace write approval

**An authenticated MCP client doesn't go through the LangGraph graph** — `file_write`, `file_edit`, and `terminal` call the underlying tool directly, outside the `HumanInTheLoopMiddleware`/`permission_mode` that protects chat. To close that gap without introducing per-call friction (the point of MCP is to operate without pausing on every tool), these 3 tools require a **persisted per-workspace approval**:

- Without approval: `file_write_tool`/`file_edit_tool`/`terminal_tool` refuse with a clear message — nothing executes.
- Approve once: `POST /workspaces/approve-mcp-write` unlocks the 3 tools for that workspace until revoked.
- Read-only tools (files, git, Context Graph, search, RAG) **never** go through this gate — no approval needed.

Every call to the 3 gated tools (approved or refused) emits a structured log (`mcp_write_call`) for auditing.

## Vectora as an MCP client

Besides being a server, Vectora also consumes third-party MCP servers — configured in **Settings → Environment → Plugins**, with support for `stdio`, `sse`, and `http` transports. See [Using settings](../../guides/using-settings).

---
title: Introduction
weight: 1
---

## What Vectora is

Vectora is a **self-hosted AI agent** for development teams. It runs entirely on your server — your VPS, your local machine, your company's server — and solves the problem most AI assistants ignore: **making the agent truly know your project**, not just generate generic code.

This happens through two complementary paths:

- **Hybrid RAG** — indexing code, docs, and past decisions with keyword search (BM25) + dense vector search + reranking, so the agent answers based on what was indexed, not on what it "thinks" is true.
- **Native Context Graph** — a workspace knowledge graph (functions, classes, concepts, and how they relate), built via AST parsing (tree-sitter) and LLM semantic extraction. Complements RAG with structural context embeddings alone can't capture.

## Architecture in one picture

```text
You (CLI / Web Chat / MCP client)
        │
        ▼
   Orchestrator (create_deep_agent — LangGraph + deepagents)
        │
   ┌────┴────┐
   ▼         ▼
 coder     search      ← specialized subagents
   │         │
   └────┬────┘
        ▼
  70+ native tools (files, git, terminal, RAG, web, integrations)
        │
        ▼
  SQLite + LanceDB (lite, default)  or  Postgres + Qdrant + Redis (complete)
```

The **orchestrator** is the supervisor: it answers directly for simple questions, or delegates to a specialized subagent (`coder` for file/git/terminal operations, `search` for web search and RAG) through human-in-the-loop (HITL) middleware that pauses before destructive actions for your approval.

## Four ways to use it

The same backend serves four different surfaces, at the same time:

1. **Web chat** — multi-user React interface, with a workbench (files, git, terminal, RAG, Context Graph) — see [Using the chat](../guides/using-the-chat) and [Using the workbench](../guides/using-the-workbench).
2. **CLI** — `vectora start`, `vectora config`, `vectora storage` — see the [CLI reference](../reference/cli).
3. **MCP server** — mounted at `/mcp` in the same process, always on. Connect Claude Code, Claude Desktop, or any MCP client — see [MCP server](../reference/mcp-server).
4. **REST API** — `/v1/classify`, `/v1/extract`, and `/v1/jobs` endpoints to integrate the agent into other systems — see [API reference](../api-reference/overview).

## Free vs. Pro

Vectora is **commercial, closed-source software** — you run it on your own infrastructure, but the code belongs to Vectora Company (same model as Cursor, Linear, Notion).

- **Free** — 100% local, no account, no dependency on Vectora Company whatsoever. You bring your own API keys (LLM, Cohere/Voyage for embeddings, Tavily for web search). Lite storage (SQLite + LanceDB).
- **Pro** — optional, covers trial/billing/licensing through `services.vectora.company` (a small Cloudflare Worker, not a "Vectora Cloud" hosting your instance). Unlocks multi-user web chat, complete storage (Postgres + Qdrant + Redis), webhooks, and the REST API with a higher rate limit.

See [current pricing](https://vectora.company/#pricing).

## Next step

→ [Installation](../installation)

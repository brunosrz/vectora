---
title: Documentation
type: docs
cascade:
  type: docs
sidebar:
  open: true
---

Vectora is a **self-hosted AI workspace** — it runs entirely on your own server, and you and the agent work side by side in the same filesystem, terminal, git, and browser. It ships with a full multi-user web chat and a native connector client for MCP servers you choose to install.

At its core, Vectora closes the **knowledge gap** between an LLM and your current codebase, docs, and stack: a hybrid **RAG** pipeline (BM25 + dense vectors + reranker) for similarity retrieval, and a native **Context Graph** (workspace analyzed via tree-sitter + LLM extraction) for structural context.

## Where to start

| I want to...                             | Go to                                          |
| ----------------------------------------- | ----------------------------------------------- |
| Install Vectora                           | [Installation](./getting-started/installation)   |
| Run it in 5 minutes                       | [Quick start](./getting-started/quick-start) |
| Understand the RAG pipeline               | [RAG & Context Graph](./concepts/rag)          |
| Connect an MCP server (as a client)       | [MCP client](./reference/mcp-client)         |
| See all CLI commands                      | [CLI reference](./reference/cli)             |
| Deploy on a server                        | [Requirements](./deployment/requirements)      |
| Understand auth, secrets, and BYOK        | [Security](./security/authentication)          |

## What Vectora is (and isn't)

Vectora is **commercial, closed-source software** — it isn't open source. You run it on your own infrastructure (your server, your VPS, your desktop), but the source code belongs to Vectora Company. It's the same model as Cursor, Linear, or Notion: the infra is yours, the code is the vendor's.

- **Free** runs 100% locally, no account required. You bring your own API keys.
- **Pro** is optional and covers trial/billing/licensing via `services.vectora.company`, a small Cloudflare Worker — it isn't a "Vectora Cloud" that hosts or runs your instance for you. Upgrading changes which features are available (high-performance storage stack, multi-user web chat, webhook-triggered automations), never where the agent runs.

See the [pricing page](https://vectora.company/#pricing) for current plans.

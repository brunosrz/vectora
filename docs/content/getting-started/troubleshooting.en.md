---
title: Troubleshooting
weight: 6
---

## The model selector is empty

No LLM provider has an API key configured. Go to **Settings → Preferences → General** (or edit `.env`/`~/.vectora/.env`) and add at least one: `GOOGLE_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `COHERE_API_KEY`, or configure a local Ollama endpoint.

## RAG returns no results / embedding errors

RAG depends on `COHERE_API_KEY` (or a VoyageAI key configured as an alternative) to generate embeddings and rerank. Without it, indexing fails silently or vector search returns nothing. Check the key in **Settings → Environment → Envs**.

## The agent can't write files / run commands

The workspace is probably still **untrusted**. See [First workspace](../first-workspace) — click "Trust this folder" to unlock writes and the terminal.

## An external MCP client (Claude Code, Claude Desktop) won't connect

Confirm Vectora is running and that the URL used is `http://<your-host>:<port>/mcp` (not `/mcp/sse` — the server is mounted directly at `/mcp` via SSE in the same process). In production, use your server's public HTTPS URL. See [MCP server](../../reference/mcp-server).

## `vectora storage complete` won't connect to Postgres/Qdrant/Redis

Complete mode requires all three services to be reachable at the configured DSNs (`POSTGRES_DSN`, `QDRANT_URL`, `REDIS_URL`). If you don't have your own infrastructure, run `scons docker` (from the monorepo root, if running from source) or use the `vectora storage wizard` to set up a managed provider (Supabase, Neon, Qdrant Cloud). See [Storage: lite vs. complete](../../concepts/storage).

## Pro features (multi-user chat, complete storage) don't unlock despite an active subscription

Confirm your `VECTORA_TOKEN` from the [dashboard](https://vectora.company/dashboard) is configured and valid — license status is cached locally with a short TTL; force a revalidation by restarting the app or checking **Settings → Administration → System**.

## `command not found: vectora` error (source install)

Run with `uv run vectora ...` instead of `vectora ...` directly — `uv` manages the virtual environment and entrypoint without a global install.

## Where to report a bug

[GitHub Issues](https://github.com/vectora-company/vectora/issues) (public) or the form at [vectora.company/issues](https://vectora.company/issues).

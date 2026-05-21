# Vectora v0.1.0rc1

**Vectora** is an open-source AI assistant for developers, built to run as a sub-agent inside Claude Code, Paperclip, and any MCP-compatible orchestrator. Local-first, self-hosted, zero mandatory infrastructure.

---

## What's included

**Multi-agent architecture**
A Supervisor classifies every incoming message and routes it to the right specialist. The Direct agent handles conversation, synthesis, and memory. The Search agent covers web research and RAG retrieval. The Coder agent handles files, terminal, and git. All routing is deterministic (regex-first, LLM fallback) with no ambiguity between agents.

**RAG subgraph with adaptive thresholds**
Every document query goes through a full pipeline: vector retrieval → confidence scoring → rerank (Cohere) or web fallback → context injection before the LLM responds. Thresholds are adaptive: high confidence (≥ 0.7) injects directly; mid confidence (0.4–0.7) reranks first; low confidence falls back to live web search.

**Cascading embeddings**
Web search results are automatically queued for embedding into LanceDB after every retrieval — fire-and-forget, non-blocking. The knowledge base grows passively as you use the assistant.

**14 tools across 4 categories**
Web search and URL extraction via Tavily. Semantic vector search, embedding queue, and batch ingestion via Cohere + LanceDB. Full filesystem access (read, edit, write, grep, list, terminal). Cross-session persistent memory with optional TTL.

**MCP server (stdio + SSE)**
13 tools and 4 resources exposed via Model Context Protocol. `stdio` mode for local Claude Code / Claude Desktop integration. `sse` mode for Docker-based multi-agent deployments where N Paperclip agents share a single Vectora hub — each isolated by `thread_id`.

**Background embedding worker**
Async worker with token bucket rate limiting (90 calls/min against Cohere's 100/min trial limit), exponential backoff retry, dead-letter queue after 3 attempts, and crash recovery via WAL reconciliation on startup.

**Multi-LLM support**
Google Gemini (free tier, recommended), Cohere (free tier), OpenAI, Anthropic, or Ollama for fully local inference. Switch providers at runtime via `/model` or the setup wizard.

**Security layer**
Path traversal prevention, ReDoS-safe regex validation, shell command blacklist (`rm -rf`, fork bombs, destructive sudo), and 30-second terminal execution timeout with async subprocess isolation.

**Interactive TUI**
Terminal UI built with Rich and prompt-toolkit. Colored panels per message type, live tool call feedback, debug mode toggle, session management, and multiline input via `Alt+Enter`.

**CI/CD pipeline**
GitHub Actions with lint, type check, unit/integration/e2e/stress tests, Docker build → GHCR push, VPS deploy via SSH, and PyPI publish via Trusted Publishing (no stored tokens).

---

## Prerequisites

- [[Cohere](https://dashboard.cohere.com/api-keys)](https://dashboard.cohere.com/api-keys) — required for embeddings and reranking (free tier)
- [[Tavily](https://app.tavily.com/)](https://app.tavily.com/) — required for web search (free tier)
- One LLM provider key (Google Gemini recommended — free tier)

---

## Installation

```bash
uv tool install vectora-agent
vectora setup
vectora chat
```

---

## PyPI

Package: [`[vectora-agent](https://pypi.org/project/vectora-agent/)`](https://pypi.org/project/vectora-agent/)
Imports and CLIs remain `vectora` and `vectora-mcp`.

---

## Docker

```bash
MCP_TRANSPORT=sse docker compose up -d
```

Image: `ghcr.io/brunosrz/vectora:latest`

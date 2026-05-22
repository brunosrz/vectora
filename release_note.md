# Vectora v0.1.0rc3

**Vectora** is an open-source AI assistant for developers, built to run as a sub-agent inside Claude Code, Paperclip, and any MCP-compatible orchestrator. Local-first, self-hosted, zero mandatory infrastructure.

---

## What's new in rc2

**Orchestrator — generalist agent replaces the supervisor router**
The supervisor was a pure router: one LLM call to decide the destination, then a second call inside the target agent. The new Orchestrator is the primary agent. It can respond directly for greetings, knowledge questions, and synthesis — no routing hop needed. When delegation is necessary, it crafts an explicit `task_query` (1–3 focused sentences) for the sub-agent instead of passing raw conversation history. Sub-agents (coder, search) read `orchestrator_task` from state and treat it as their primary directive, reducing ambiguity on long multi-turn sessions.

**Artifact tool (`create_artifact`)**
Agents now explicitly call `create_artifact` to persist structured documents. Supported types: `plan`, `spec`, `task_list`, `overview`, `guide`, `architecture`, `implementation`. Files are saved to `~/.vectora/artifacts/{session_id}/{slug}.md` and the tool returns structured metadata (path, title, type, timestamp). No heuristic detection — the agent decides when a document is worth persisting.

**Project context loading**
On the first turn of each session, Vectora scans the current working directory recursively for `AGENTS.md`, `CLAUDE.md`, and `GEMINI.md`. Any files found are injected as context so the agent immediately understands project conventions, architecture, and coding standards. The result is persisted in state and not re-scanned on subsequent turns.

**Session tracer**
A lightweight async SQLite-backed tracer records every orchestrator routing decision and agent span with timing data. Useful for debugging routing behavior and building observability tooling on top.

**Verbosity levels (0–5)**
`/debug` now accepts a level from 0 to 5 instead of a boolean toggle. Level 0 is silent, level 5 shows full tool payloads and LLM internals. Displayed as a Rich table with descriptions per level.

**Session per working directory**
On startup, Vectora automatically resumes the last session used in the current directory. Opening a new terminal in a different project gets an independent session. `/new` creates a new session and associates it with the current directory. `/session <id>` switches manually and updates the mapping.

**Unified CLI**
`vectora` and `vectora-mcp` are now the only entry points. The setup wizard, chat loop, and MCP server are all reachable from a single install.

**CI/CD hardening**
Docker build, VPS deploy, and PyPI publish now run exclusively on `v*` tags or manual `workflow_dispatch`. The `[deploy]` commit keyword is removed. Adding `[ci skip]` to any commit message skips the entire pipeline.

---

## Architecture

```
START
  └─► orchestrator (responds inline OR delegates with task_query)
        ├─► [respond]      → END
        ├─► [coder]        → coder → coder_tools ↻ → END
        ├─► [search]       → search → search_tools → process_retrieval ↻ → END
        └─► [rag_subgraph] → rag_subgraph → orchestrator (synthesis) → END
```

---

## What's included

**Multi-agent architecture**
The Orchestrator is the single entry point and primary LLM agent. It responds directly for simple queries and delegates to specialists with an explicit task description. RAG synthesis is done inline by the Orchestrator after the RAG subgraph injects context. The Search agent covers web research and cascading embeddings. The Coder agent handles files, terminal, and git.

**RAG subgraph with adaptive thresholds**
Every document query goes through a full pipeline: vector retrieval → confidence scoring → rerank (Cohere) or web fallback → context injection before the LLM responds. Thresholds are adaptive: high confidence (≥ 0.7) injects directly; mid confidence (0.4–0.7) reranks first; low confidence falls back to live web search.

**Cascading embeddings**
Web search results are automatically queued for embedding into LanceDB after every retrieval — fire-and-forget, non-blocking. The knowledge base grows passively as you use the assistant.

**15 tools across 5 categories**
Web search and URL extraction via Tavily. Semantic vector search, embedding queue, and batch ingestion via Cohere + LanceDB. Full filesystem access (read, edit, write, grep, list, terminal). Artifact persistence via `create_artifact`. Cross-session persistent memory with optional TTL.

**MCP server (stdio + SSE)**
13 tools and 4 resources exposed via Model Context Protocol. `stdio` mode for local Claude Code / Claude Desktop integration. `sse` mode for Docker-based multi-agent deployments where N Paperclip agents share a single Vectora hub — each isolated by `thread_id`.

**Background embedding worker**
Async worker with token bucket rate limiting (90 calls/min against Cohere's 100/min trial limit), exponential backoff retry, dead-letter queue after 3 attempts, and crash recovery via WAL reconciliation on startup.

**Multi-LLM support**
Google Gemini (free tier, recommended), Cohere (free tier), OpenAI, Anthropic, or Ollama for fully local inference. Switch providers at runtime via `/model` or the setup wizard.

**Security layer**
Path traversal prevention, ReDoS-safe regex validation, shell command blacklist (`rm -rf`, fork bombs, destructive sudo), and 30-second terminal execution timeout with async subprocess isolation.

**Interactive TUI**
Terminal UI built with Rich and prompt-toolkit. Colored panels per message type, live tool call feedback, verbosity levels (0–5), session management, and multiline input via `Alt+Enter`.

**CI/CD pipeline**
GitHub Actions with lint, unit/integration/e2e/stress tests, Docker build → GHCR push, VPS deploy via SSH, and PyPI publish via Trusted Publishing. Docker/deploy/PyPI gated to `v*` tags only.

---

## Prerequisites

- [Cohere](https://dashboard.cohere.com/api-keys) — required for embeddings and reranking (free tier)
- [Tavily](https://app.tavily.com/) — required for web search (free tier)
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

Package: [`vectora-agent`](https://pypi.org/project/vectora-agent/)
Imports and CLIs remain `vectora` and `vectora-mcp`.

---

## Docker

```bash
MCP_TRANSPORT=sse docker compose up -d
```

Image: `ghcr.io/brunosrz/vectora:latest`

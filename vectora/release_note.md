# Vectora v0.1.0rc4

**Vectora** is an open-source AI assistant for developers, built to run as a sub-agent inside Claude Code, Paperclip, and any MCP-compatible orchestrator. Local-first, self-hosted, zero mandatory infrastructure.

---

## What's new in rc4

### RAG hotfix — 4 bugs resolved

**pandas declared as a first-class dependency**
`vector_search` and `manage_retriever` use LanceDB's `.to_pandas()` — but `pandas` was never declared in `pyproject.toml`. Any environment installed via `uv tool` silently failed with `ModuleNotFoundError`, making local RAG completely inaccessible. Fixed by declaring `pandas` as a dependency and adopting it idiomatically: `manage_retriever` now uses vectorized DataFrame operations (boolean masks, `.map()`) instead of row-by-row loops; the `/rag` panel loads `.to_pandas()` per collection to display the curated vs web-search origin breakdown.

**Orchestrator ↔ RAG subgraph recursion loop eliminated**
Querying the RAG subgraph caused a `GraphRecursionError` (limit 25). Root cause: `rag_inject` returned an empty dict when no docs were found, so the orchestrator never received the `rag_context` signal and re-routed to `rag` indefinitely. Fix: `rag_inject` now always emits `SystemMessage(name="rag_context")` — even when empty — as a deterministic turn marker. The orchestrator detects this marker via `_is_post_rag()` and enters a synthesis-only path (`_synthesize_after_rag()` → `END`), making the loop structurally impossible.

**Multi-collection RAG — all indexed content now reachable**
`_call_vector_search_all` previously searched only two hardcoded collections (`articles` + `web_cache`). Content indexed via `/rag add docs/` landed in a `docs` collection that was never queried. Fixed by discovering all LanceDB tables dynamically via `table_names()` and querying them in parallel (`asyncio.gather`). Collections matching `rag_collection_web` have `metadata["origin"]="web_search"` injected so the LLM and reranker can weigh source trust.

**Distance vs similarity inversion corrected**
Without Cohere reranking, `vector_search` returns `_distance` (L2 — lower is better). The subgraph was reading it as a similarity score (higher is better), inverting routing logic: an exact match (distance ~0.1) triggered web fallback; a poor match (distance ~0.9) went straight to inject. Fixed via `_result_score()`: converts L2 distance to a bounded similarity `1 / (1 + distance)` ∈ (0, 1].

---

### Anti-contamination for RAG web content

**Isolated web bucket**
Web results from `web_search` and `fetch_url` cascade now land in a dedicated `web_cache` collection instead of the shared `articles` collection. User-curated content (indexed via `ingest_docs` or `/rag add`) is never mixed with live web results.

**Curation gate — reranker + LLM judge**
New `web_curation.py` module. No web result is persisted without passing two gates: Cohere reranker scores each candidate against the current query/task, filtering below `web_persist_min_score`; a batch LLM judge evaluates survivors against `project_context` + `orchestrator_task` and returns a `keep/discard` verdict per document. Only approved content reaches the embedding queue.

**`manage_retriever` tool**
New tool with three actions: `list` (audit indexed docs by source and origin), `delete` (remove by source URL), `purge` (clear an entire collection). Useful when authoritative sources replace previously cached web content.

---

### `.vectoraignore` support

Vectora now respects both `.gitignore` and `.vectoraignore` when indexing files via `ingest_docs` or `/rag add`. Patterns in `.vectoraignore` follow the same gitignore syntax and are applied on top of `.gitignore` rules, giving per-project control over what enters the knowledge base without touching the git ignore file.

---

### Rate limit UI for the main LLM

When the LLM provider (Gemini, OpenAI, etc.) returns a 429, the TUI now displays a styled yellow panel — `[Vectora] ⚠️ Quota / Rate Limit` — instead of dumping the raw API error JSON to the terminal. `_is_llm_quota_error()` detects 429, `resource_exhausted`, `rateLimitExceeded`, and quota-related strings across providers.

---

### TUI improvements

**Routing-aware panel titles**
Response panels now reflect which agent actually answered:

- `[Vectora]` — orchestrator direct response or RAG synthesis
- `[Vectora RAG]` — answer synthesized after RAG pipeline
- `[Vectora Coder]` — response from the coder agent
- `[Vectora Search]` — response from the search agent

**Structured output JSON no longer leaks into chat**
The orchestrator uses `with_structured_output()` for routing decisions. `astream_events` was capturing the raw JSON tokens as if they were the response, prepending the routing decision to every message. Fixed by filtering `CHAT_MODEL_STREAM` events from the `orchestrator` node during the routing phase and capturing the final `AIMessage` from the `CHAIN_END` event instead.

**Console logging respects verbosity**
`[INFO]` log lines no longer appear in the terminal when debug is disabled (`verbosity == 0`). The `StreamHandler` level is now adjusted at runtime: `WARNING` at verbosity 0, `INFO` at 1–3, `DEBUG` at 4+. Logs continue to flow to the JSON audit file regardless of verbosity.

**Tavily v2 (`langchain-tavily`)**
Migrated from `tavily-python` to `langchain-tavily`. Unlocks `topic` (general / news / finance), `time_range`, `include_raw_content`, `include_images`, and per-call `include_domains` / `exclude_domains` filtering. New `tavily_extract` tool replaces `fetch_url` for multi-URL batch extraction.

**Cohere asymmetric embeddings**
Embedding calls now pass the correct `input_type` to the Cohere API: `search_document` at index time, `search_query` at query time. This is the intended usage of Cohere's asymmetric embedding model and measurably improves retrieval quality.

**`langchain-mcp-adapters` integration**
The MCP client (`vectora/tools/mcp.py`) now uses `MultiServerMCPClient` from the official `langchain-mcp-adapters` library. Gains: OAuth per-server auth, resource loading (file blobs), persistent sessions, `allowedTools` / `disabledTools` filtering, `structuredContent` for typed return values.

**LangGraph Studio**
`langgraph.json` added at the repo root. Run `langgraph dev` for a local UI at `http://127.0.0.1:2024` with real-time node/edge visualization, per-step state inspection, time-travel debugging, and state forking.

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
The Orchestrator is the single entry point and primary LLM agent. It responds directly for simple queries and delegates to specialists with an explicit task description. RAG synthesis is done inline by the Orchestrator after the RAG subgraph injects context.

**RAG subgraph with adaptive thresholds**
Every document query goes through a full pipeline: vector retrieval → confidence scoring → rerank (Cohere) or web fallback → context injection. Thresholds: high confidence (≥ 0.7) injects directly; mid confidence (0.4–0.7) reranks first; low confidence falls back to live web search. All collections are searched in parallel — no orphaned indexed content.

**Web content anti-contamination**
Web results land in a separate `web_cache` collection. A curation gate (Cohere reranker + LLM judge) filters every candidate before it reaches the embedding queue. User-curated content in `articles` is never overwritten by live web results.

**16 tools across 5 categories**
Web (`web_search`, `fetch_url`). RAG (`vector_search`, `embedding`, `ingest_docs`, `manage_retriever`). Files (`file_read`, `file_edit`, `file_write`, `grep`, `list_dir`, `terminal`). Artifacts (`create_artifact`). Memory (`save_memory`, `get_memory`, `delete_memory`). All tools are available to all agents — specialization comes from system prompts, not tool restrictions.

**MCP server (stdio + SSE)**
Tools and resources exposed via Model Context Protocol. `stdio` mode for local Claude Code / Claude Desktop. `sse` mode for Docker-based deployments where multiple agents share a single Vectora hub.

**Background embedding worker**
Async worker with token bucket rate limiting (90 calls/min), exponential backoff retry, dead-letter queue after 3 attempts, and WAL crash recovery on startup.

**Multi-LLM support**
Google Gemini (free tier, recommended), Cohere, OpenAI, Anthropic, or Ollama for fully local inference.

**Interactive TUI**
Rich + prompt-toolkit. Agent-aware panel titles, structured output JSON filtering, verbosity-gated console logging, rate limit UI for LLM and embedding providers.

---

## Prerequisites

- [Cohere](https://dashboard.cohere.com/api-keys) — required for embeddings and reranking (free tier)
- [Tavily](https://app.tavily.com/) — required for web search (free tier)
- One LLM provider key (Google Gemini recommended — free tier)

---

## Installation

```bash
uv tool install vectora
vectora setup
vectora chat
```

---

## PyPI

Package: [`vectora`](https://pypi.org/project/vectora/)
Imports and CLIs remain `vectora` and `vectora-mcp`.

---

## Docker

```bash
MCP_TRANSPORT=sse docker compose up -d
```

Image: `ghcr.io/brunosrz/vectora:latest`

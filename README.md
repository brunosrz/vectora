# <img src="assets/vectora.svg" width="32" height="32"> Vectora

**Vectora** is a self-hosted AI assistant built for development teams — runs entirely on your server, integrates as a sub-agent in any MCP-compatible orchestrator (Claude Code, Claude Desktop, VS Code extensions), and ships with a full multi-user web chat.

At its core, Vectora solves the **knowledge gap problem**: LLMs don't know your codebase, your docs, or the latest versions of your stack. Vectora bridges that gap with hybrid RAG (BM25 + dense vectors + Cohere reranker) — ingest your docs once, and every AI interaction becomes contextually aware.

---

## Why Vectora?

- **Orchestrator + Specialized Agents** — The Orchestrator is the primary LLM agent. It answers directly for simple queries and delegates with explicit task instructions to specialists (search, coder, RAG). No wasted routing hops.
- **Hybrid RAG pipeline** — Every retrieval runs BM25 + dense vector search + Cohere reranker. Results flow back to the Orchestrator for synthesis.
- **20+ tools across 6 categories** — Web search, vector search, filesystem, terminal (PTY), artifacts, memory — always available.
- **Cascading embeddings** — Web search results pass a curation gate (Cohere reranker + LLM judge) before being embedded. Your curated knowledge base is never contaminated.
- **Multi-user web chat** — Built-in Next.js interface with authentication, RBAC, workspaces, embedded terminal, diff viewer, and plan panel.
- **Persistent cross-session memory** — SQLite-backed memory with user isolation.
- **Zero infrastructure for lite mode** — SQLite + LanceDB. No Docker or Postgres required for local or small-team use.
- **Multi-LLM** — Google Gemini (free tier), Cohere, OpenAI, Anthropic, or Ollama (fully local).

---

## Architecture

### Orchestrator + Workers

| Agent            | Responsibility                                              | Tools                                                                  |
| ---------------- | ----------------------------------------------------------- | ---------------------------------------------------------------------- |
| **orchestrator** | Primary LLM agent — responds directly OR delegates          | `create_artifact`, `save_memory`, `get_memory`, `delete_memory`        |
| **search**       | Web research, real-time info, cascading embeddings          | `web_search`, `web_fetch`, `web_crawl`, `web_map`, `vector_search`     |
| **coder**        | File operations, terminal commands, code generation         | `file_read`, `file_edit`, `file_write`, `grep`, `list_dir`, `terminal` |
| **rag**          | Retrieve → score → rerank/websearch → inject → orchestrator | `vector_search`, `embedding`, `ingest_docs`, `manage_retriever`        |

### RAG Subgraph

| Score   | Path                                                                  |
| ------- | --------------------------------------------------------------------- |
| ≥ 0.7   | `rag_inject` directly — high confidence                               |
| 0.4–0.7 | `rag_rerank` → `rag_inject`                                           |
| < 0.4   | `search` (with `rag_pending=True`) → `search_finalize` → `rag_inject` |

---

## Prerequisites

| Requirement        | Notes                                                                       |
| ------------------ | --------------------------------------------------------------------------- |
| **Python 3.13+**   | Managed by [uv](https://docs.astral.sh/uv/)                                 |
| **Node.js 22+**    | For the web chat (`pnpm` required)                                          |
| **Cohere API key** | Embeddings + reranking — [free tier](https://dashboard.cohere.com/api-keys) |
| **Tavily API key** | Web search — [free tier](https://app.tavily.com/)                           |
| **LLM provider**   | Google Gemini (free tier), OpenAI, Anthropic, Cohere, or Ollama             |

---

## Quickstart (from source)

```bash
git clone https://github.com/brunosrz/vectora.git
cd vectora

# Install Python dependencies
uv sync

# Copy and fill in your API keys
cp .env.example .env
# Edit .env: GOOGLE_API_KEY, COHERE_API_KEY, TAVILY_API_KEY

# Install web chat dependencies
pnpm --dir chat install

# Start backend (port 8080) + web chat (port 3000) simultaneously
scons dev
```

Open `http://localhost:3000`. The first user to sign up becomes the root administrator.

### CLI only (no web chat)

```bash
# Interactive textual chat
uv run vectora chat

# MCP server (stdio — for Claude Code / Claude Desktop)
uv run vectora server mcp --transport stdio

# API only — no Next.js bundle, no frontend proxy
uv run vectora server headless --port 8080
```

---

## MCP Integration

Add to `.mcp.json` in your project or `~/.claude/mcp.json` globally:

```json
{
  "mcpServers": {
    "Vectora": {
      "command": "uv",
      "args": ["run", "vectora", "server", "mcp", "--transport", "stdio"]
    }
  }
}
```

Remote MCP server over SSE:

```json
{
  "mcpServers": {
    "Vectora": {
      "url": "https://vectora.yourdomain.com/mcp/sse"
    }
  }
}
```

---

## Build targets (SCons)

The build system uses [SCons](https://scons.org/), bundled as a dev
dependency. Use it directly from PowerShell, cmd, bash or zsh — no
shell-specific syntax required.

### Final product (from zero to installer)

```
scons release          Full build + native installer for the current OS
scons release-win      Windows installer (.msi + .exe NSIS)
scons release-mac      macOS installer (.dmg universal x64+arm64)
scons release-linux    Linux installers (.AppImage + .deb + .rpm)
```

The pipeline runs in sequence:

```
build-chat (1-2 min)  -->  build-nuitka (10-30 min)  -->  build-desktop  -->  package
chat/out/                  dist-nuitka/vectora.exe      desktop/dist/        desktop/dist-electron/
```

### Individual steps

```
scons build-chat       Next.js build + static export -> chat/out/
scons build-nuitka     Nuitka onefile binary -> dist-nuitka/  (10-30 min first run)
scons build-desktop    Electron TypeScript -> desktop/dist/
scons package          electron-builder -> desktop/dist-electron/  (uses existing dist-nuitka/)
scons install-desktop  pnpm install in desktop/
```

### Development

```
scons dev              Backend (8080) + Next.js dev (3000), Ctrl+C stops both
scons dev-backend      Backend only
scons dev-chat         Next.js dev only
```

### Quality

```
scons test             pytest tests/unit/
scons lint             ruff + ty + tsc + oxlint
scons clean            Remove dist-nuitka/ chat/out/ desktop/dist*
scons help             Full list with descriptions
```

**Note:** On Windows, just open PowerShell or cmd at the project root and
run `scons release-win`. No Git bash, no shell tricks needed.

---

## Docker

```bash
cp .env.example .env
# Edit .env with your API keys

docker compose up -d
# Web chat: http://localhost:8080
```

VPS with HTTPS (Traefik):

```bash
cp .env.example .env
# Set VECTORA_DOMAIN and ACME_EMAIL

docker network create traefik-public
docker compose -f docker-compose.yml -f docker-compose.traefik.yml up -d
# Web chat: https://vectora.yourdomain.com
```

---

## CLI Reference

```
vectora [command] [options]

Commands:
  (default) / chat     Interactive textual chat (resumes last session)
  server chat          FastAPI + web chat (serves bundled Next.js or proxies to dev server)
  server mcp           MCP server (stdio or SSE transport)
  server headless      FastAPI only — no web UI, no frontend proxy (for API integrations)
  setup                Interactive first-time configuration wizard
  license              Show or manage license status
  auth                 Login / logout / whoami
  traces               View internal observability traces
  sessions             List all saved sessions
  config               Show or edit settings

Global options:
  --model <name>       Switch LLM provider/model (e.g. gemini-2.5-flash)
  --new                Force a new conversation session
  --session <id>       Resume a specific session
  --verbosity <0-5>    Console output detail level
  --port <n>           Port for server commands (default: 8080)
```

---

## Data & Persistence

All data is stored in `~/.vectora/`:

```
~/.vectora/
├── config.toml             # Runtime configuration (providers, storage backend)
├── auth.key                # JWT signing key (auto-generated, perm 600)
├── data/
│   ├── vectora.db          # Users, sessions, memories, checkpoints (SQLite WAL)
│   ├── embedding_queue.db  # Async embedding queue (SQLite)
│   ├── traces.db           # Observability spans (SQLite)
│   └── lancedb/            # Vector store (LanceDB)
├── artifacts/              # Plans, specs, guides (create_artifact output)
│   └── {session_id}/*.md
├── secrets/
│   ├── system.kdbx         # System secrets vault (KeePassXC format)
│   └── users/{id}.kdbx     # Per-user vault (API keys, SSH keys)
├── skills/{user_id}/       # Installed skills (SKILL.md format)
├── safe_roots.json         # Admin-configured trusted paths
├── workspaces.json         # Registered workspaces
└── license_cache.json      # Cached license validation (TTL 6h / 48h offline)
```

---

## Tools Reference

| Category      | Tools                                                                                                       |
| ------------- | ----------------------------------------------------------------------------------------------------------- |
| **Web**       | `web_search`, `web_fetch`, `web_crawl`, `web_map`, `web_research`, `web_get_research`                       |
| **RAG**       | `vector_search`, `embedding`, `ingest_docs`, `manage_retriever`                                             |
| **Files**     | `file_read`, `file_edit`, `file_write`, `grep`, `list_dir`, `terminal`                                      |
| **Artifacts** | `create_artifact`                                                                                           |
| **Memory**    | `save_memory`, `get_memory`, `delete_memory`                                                                |
| **Git**       | `git_status`, `git_log`, `git_diff`, `git_branch`, `git_checkout`, `git_commit`, `git_push`, `gh_pr_create` |

---

## Tech Stack

| Layer            | Technology                                                                                             |
| ---------------- | ------------------------------------------------------------------------------------------------------ |
| Language         | Python 3.13+ / [uv](https://docs.astral.sh/uv/)                                                        |
| Agent framework  | [LangChain](https://langchain.com/) + [LangGraph](https://langchain-ai.github.io/langgraph/)           |
| Vector store     | [LanceDB](https://lancedb.github.io/lancedb/) (lite) / Qdrant (pro)                                    |
| Embeddings       | Cohere `embed-multilingual-v3.0` + `rerank-multilingual-v3.0`                                          |
| Persistence      | SQLite + `aiosqlite` (WAL) + LangGraph Checkpointer                                                    |
| Web chat         | Next.js 16 + Hono + Zustand + shadcn/ui + Tailwind                                                     |
| Terminal         | PTY via `pywinpty` (Win) / `ptyprocess` (Unix) + xterm.js                                              |
| Context protocol | [MCP](https://modelcontextprotocol.io/) via [FastMCP](https://github.com/jlowin/fastmcp)               |
| CLI UI           | [Rich](https://rich.readthedocs.io/) + [prompt-toolkit](https://python-prompt-toolkit.readthedocs.io/) |

---

## Configuration

API keys go in `~/.vectora/config.toml` (created by `vectora setup`) or a local `.env`:

```env
# LLM Provider (auto-detected from available keys if not set)
LLM_PROVIDER=google-genai
GOOGLE_API_KEY=your_key_here

# Required: RAG embeddings + reranking
COHERE_API_KEY=your_key_here

# Required: Web search + URL extraction
TAVILY_API_KEY=your_key_here

# Optional: tracing
LANGSMITH_TRACING=false
LANGSMITH_API_KEY=your_key_here
```

---

## License

Proprietary. See [LICENSE](./LICENSE).

<!-- mcp-name: io.github.brunosrz/vectora -->

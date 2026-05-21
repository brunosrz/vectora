# Vectora

**Vectora** is an open-source AI assistant (Apache 2.0) built for developers — local-first, self-hosted, and designed to run as a powerful sub-agent inside any MCP-compatible orchestrator (Claude Code, Claude Desktop, Paperclip, VS Code extensions).

At its core, Vectora solves the **knowledge gap problem**: LLMs don't know your codebase, your docs, or the latest versions of your stack. Vectora bridges that gap with RAG (Retrieval-Augmented Generation) — ingest your docs once, and every AI interaction becomes contextually aware.

---

## Why Vectora?

- **Supervisor + Specialized Agents**: A router classifies every message and delegates to the right specialist — search agent for web/RAG, coder agent for files and terminal, direct agent for conversation and synthesis.
- **RAG-native subgraph**: Every query goes through a full retrieve → score → rerank → inject pipeline before hitting the LLM.
- **14 tools across 4 categories**: Web search, vector search, file system, memory — each agent sees only the tools it needs.
- **Cascading embeddings**: Web search results are automatically queued for embedding into LanceDB (fire-and-forget), building your knowledge base as you chat.
- **Sub-agent architecture**: Runs as an MCP server. Claude Code delegates complex tasks to Vectora; Vectora reasons, routes, and responds.
- **Persistent memory**: Cross-session memory in SQLite. Vectora remembers your preferences, project context, and decisions.
- **Zero infra**: SQLite + LanceDB. No Docker required for local use.
- **Multi-LLM**: Google Gemini (free tier), Cohere (free tier), OpenAI, Anthropic, or Ollama (fully local).

---

## Architecture

### Supervisor + Workers

Every message enters through a single entry point and is routed by the **Supervisor** to the right specialized agent:

```
START
  └─► supervisor (classify intent)
        ├─► direct    ──► direct_tools (memory) ──► direct ──► END
        ├─► search    ──► search_tools ──► process_retrieval ──► search ──► END
        ├─► coder     ──► coder_tools (fs + memory) ──► coder ──► END
        └─► rag_subgraph ──────────────────────────────────────► direct ──► END
```

| Agent          | Responsibility                                                               | Tools                                                                  |
| -------------- | ---------------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| **supervisor** | Classifies intent via regex + LLM fallback, routes via `Command(goto=...)`   | —                                                                      |
| **direct**     | General conversation, synthesis after RAG, memory management                 | `save_memory`, `get_memory`, `delete_memory`                           |
| **search**     | Web research, real-time info, builds knowledge base via cascading embeddings | `web_search`, `fetch_url`, `vector_search`                             |
| **coder**      | File operations, terminal commands, code generation                          | `file_read`, `file_edit`, `file_write`, `grep`, `list_dir`, `terminal` |

### RAG Subgraph

When the supervisor routes to `rag`, a dedicated subgraph runs the full retrieval pipeline before synthesis:

```
rag_retrieve (vector_search)
  └─► rag_decide (score threshold)
        ├─► rag_inject     (score ≥ 0.7 — high confidence, inject directly)
        ├─► rag_rerank     (score 0.4–0.7 — rerank with Cohere before inject)
        └─► rag_websearch  (score < 0.4 — fall back to web + auto-embed results)
```

Results are injected as a `SystemMessage` into context before the `direct` agent synthesizes the final answer.

### Cascading Embeddings

After any `web_search` or `fetch_url` call, `process_retrieval` automatically queues the results for embedding into LanceDB — fire-and-forget, no blocking. Your vector store grows passively as you use web search.

---

## Prerequisites

### Cohere — Required

Vectora uses [Cohere](https://cohere.com/) for embeddings (`embed-multilingual-v3.0`) and reranking (`rerank-multilingual-v3.0`). It offers a **generous free tier** with first-class LangChain integration.

Get your key: https://dashboard.cohere.com/api-keys

### Tavily — Required

Vectora uses [Tavily](https://tavily.com/) for real-time web search and URL content extraction. It offers a **generous free tier** optimized for AI agents.

Get your key: https://app.tavily.com/

### LLM Provider — Choose One

| Provider                         | Free Tier | Get Key                                                       |
| -------------------------------- | --------- | ------------------------------------------------------------- |
| **Google Gemini** ✅ Recommended | Yes       | [aistudio.google.com](https://aistudio.google.com/app/apikey) |
| Cohere                           | Yes       | [dashboard.cohere.com](https://dashboard.cohere.com/api-keys) |
| Ollama (local)                   | No cost   | [ollama.ai](https://ollama.ai)                                |
| OpenAI                           | Paid      | [platform.openai.com](https://platform.openai.com/api-keys)   |
| Anthropic                        | Paid      | [console.anthropic.com](https://console.anthropic.com/)       |

---

## Installation

### Option 1: UV (Recommended)

```bash
# Install globally
uv tool install vectora-agent

# First-time setup (interactive wizard)
vectora setup

# Start chatting
vectora chat
```

### Option 2: From Source

```bash
git clone https://github.com/brunosrz/vectora.git
cd vectora

# Install with all dependencies
uv sync

# Configure your keys
cp .env.example .env
# Edit .env with your GOOGLE_API_KEY and COHERE_API_KEY

# Run
uv run vectora chat
```

### Option 3: Docker

```bash
# Copy and configure environment
cp .env.example .env
# Edit .env with your API keys

# Run the chat interface
docker compose run --rm vectora

# Or run as MCP server (multi-agent mode)
MCP_TRANSPORT=sse docker compose up -d
```

---

## Running Modes

### Chat Mode (Interactive TUI)

The primary interface — a terminal dashboard built with Rich.

```bash
vectora chat
```

Features: multi-turn conversation, session history, live tool feedback (colored panels), debug mode toggle, model switching.

### MCP Server — Local (stdio)

Run Vectora as an MCP sub-agent for Claude Code or Claude Desktop.

```bash
vectora mcp-server
```

### MCP Server — Remote (SSE, Multi-Agent)

Run Vectora as a shared hub for multiple Paperclip agents or orchestrators connecting simultaneously.

```bash
MCP_TRANSPORT=sse MCP_PORT=8000 vectora mcp-server
```

Each client passes its own `thread_id` — sessions are fully isolated.

### Setup Wizard

Interactive configuration to set up API keys, choose LLM provider, and test connectivity.

```bash
vectora setup
```

---

## Connecting to Claude Code / Claude Desktop

Add Vectora to your `.mcp.json` (in your project root):

```json
{
  "mcpServers": {
    "Vectora-MCP": {
      "command": "uv",
      "args": ["run", "--project", "/absolute/path/to/vectora", "vectora-mcp"]
    }
  }
}
```

For a globally installed Vectora:

```json
{
  "mcpServers": {
    "Vectora-MCP": {
      "command": "vectora-mcp"
    }
  }
}
```

For Docker (SSE mode, multiple agents):

```json
{
  "mcpServers": {
    "Vectora-MCP": {
      "url": "http://localhost:8000/sse"
    }
  }
}
```

---

## Chat Commands

| Command         | Description                                                |
| --------------- | ---------------------------------------------------------- |
| `/help`         | Show quick help                                            |
| `/list`         | Show all commands                                          |
| `/tools`        | List available tools                                       |
| `/model`        | List or switch models                                      |
| `/debug`        | Toggle debug mode (shows tool calls and routing decisions) |
| `/new`          | Start a new session                                        |
| `/sessions`     | List all sessions                                          |
| `/session <id>` | Switch to a specific session                               |
| `/quit`         | Exit                                                       |

**Input shortcuts:** `Enter` sends, `Alt+Enter` or `Shift+Enter` adds a line break.

---

## Tools Reference

14 tools across 4 categories, distributed to the agent that needs them:

| Category   | Tools                                                                  | Agent                 |
| ---------- | ---------------------------------------------------------------------- | --------------------- |
| **Web**    | `web_search`, `fetch_url`                                              | search                |
| **RAG**    | `vector_search`, `embedding`, `ingest_docs`                            | search / RAG subgraph |
| **Files**  | `file_read`, `file_edit`, `file_write`, `grep`, `list_dir`, `terminal` | coder                 |
| **Memory** | `save_memory`, `get_memory`, `delete_memory`                           | direct / coder        |
| **MCP**    | `call_mcp_tool`                                                        | all                   |

---

## Data & Persistence

All data is stored locally in `~/.vectora/`:

```
~/.vectora/
├── .env                    # Your API keys
├── chat_config.json        # Persistent chat settings
├── data/
│   ├── vectora.db          # Sessions, memories, checkpoints (SQLite)
│   ├── embedding_queue.db  # Async embedding queue (SQLite)
│   └── lancedb/            # Vector store for RAG
├── logs/
│   ├── vectora.jsonl       # Structured JSON logs (rotating, 10 MB)
│   └── mcp.log             # MCP server logs
└── exports/                # Session audit trails + debug dumps
```

---

## Tech Stack

| Layer            | Technology                                                                                             |
| ---------------- | ------------------------------------------------------------------------------------------------------ |
| Language         | Python 3.14+ managed by [uv](https://github.com/astral-sh/uv)                                          |
| Agent Framework  | [LangChain](https://langchain.com/) + [LangGraph](https://langchain-ai.github.io/langgraph/)           |
| Agent Pattern    | Supervisor + Specialized Workers (direct / search / coder) + RAG Subgraph                              |
| Vector Store     | [LanceDB](https://lancedb.github.io/lancedb/) — file-based, zero-config                                |
| Embeddings       | [Cohere](https://cohere.com/) — `embed-multilingual-v3.0` + `rerank-multilingual-v3.0`                 |
| Persistence      | SQLite via `aiosqlite` + LangGraph Checkpointer                                                        |
| Context Protocol | [MCP](https://modelcontextprotocol.io/) via [FastMCP](https://github.com/jlowin/fastmcp)               |
| Terminal UI      | [Rich](https://rich.readthedocs.io/) + [prompt-toolkit](https://python-prompt-toolkit.readthedocs.io/) |
| Observability    | [LangSmith](https://smith.langchain.com/) (optional)                                                   |

---

## Configuration

All configuration goes in `~/.vectora/.env` or a project-local `.env`:

```env
# LLM Provider
LLM_PROVIDER=google-genai
GOOGLE_API_KEY=your_key_here

# Required: RAG embeddings + reranking
COHERE_API_KEY=your_key_here

# Required: Web search + URL extraction
TAVILY_API_KEY=your_key_here

# Optional: Tracing
LANGSMITH_TRACING=false
LANGSMITH_API_KEY=your_key_here
LANGSMITH_PROJECT=vectora

# Optional: Logging
LOG_LEVEL=INFO

# Feature flags
ENABLE_RAG=true
ENABLE_FILE_OPERATIONS=true
```

---

## License

Apache 2.0. See [LICENSE](./LICENSE).

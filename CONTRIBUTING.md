# Contributing to Vectora

Thank you for contributing! This guide covers everything you need to set up your environment, understand the code standards, and submit quality code.

---

## Environment Setup

### Requirements

- Python 3.14+
- [uv](https://github.com/astral-sh/uv) — package and environment manager
- Git

### Installation

```bash
# Clone
git clone https://github.com/brunosrz/vectora.git
cd vectora

# Install all dependencies (including dev and test extras)
uv sync

# Install pre-commit hooks
uv run pre-commit install
```

### Configure API Keys

Vectora requires three API keys to run. Create `~/.vectora/.env` (or a local `.env`) with:

```env
# Required: RAG embeddings + reranking
COHERE_API_KEY=your_key_here

# Required: web search + URL extraction
TAVILY_API_KEY=your_key_here

# Required: LLM provider (choose one)
LLM_PROVIDER=google-genai
GOOGLE_API_KEY=your_key_here
```

Or run the interactive wizard which guides you through all of this:

```bash
uv run vectora
```

### Verify Setup

```bash
# Run unit tests
uv run pytest tests/unit/ -v

# Check linting
uv run ruff check src/

# Check types
uv run ty check src/

# Start the chat locally
uv run vectora chat
```

---

## Running Tests

### All tests

```bash
uv run pytest tests/ -v
```

### With coverage

```bash
uv run pytest tests/ --cov=vectora --cov-report=html
# Open htmlcov/index.html for a detailed report
```

### By category

```bash
uv run pytest tests/unit/        # Unit (fast, no external I/O)
uv run pytest tests/integration/ # Integration (RAG, graph, A2A)
uv run pytest tests/e2e/         # End-to-end (full chat, MCP)
uv run pytest tests/stress/      # Stress (concurrency)
```

### Debug

```bash
uv run pytest tests/ -vv -s         # Verbose output
uv run pytest tests/ --pdb          # Breakpoint on failure
uv run pytest tests/ --lf           # Only the last failing test
uv run pytest tests/ -k "rag"       # Tests matching "rag"
```

### Coverage targets

- **Overall:** > 80%
- **tools/**, **services/**: > 85%
- **ui/**: > 60% (Rich components are hard to test)

---

## Code Standards

### Types — Required

All code must have complete type hints. Python 3.14+ syntax:

```python
# ✅ Correct
async def search_docs(query: str, limit: int = 5) -> list[dict[str, str]]:
    """Search documents in LanceDB."""
    ...

# ❌ Wrong — no types
async def search_docs(query, limit=5):
    ...
```

Use `pydantic` for data contracts between layers:

```python
from pydantic import BaseModel

class SearchResult(BaseModel):
    content: str
    score: float
    source: str | None = None
```

### Async — All I/O must be async

```python
# ✅ Correct — async for database and network
async def save_memory(key: str, content: str) -> str:
    async with aiosqlite.connect(db_path) as db:
        await db.execute("INSERT ...", (key, content))
        await db.commit()

# ❌ Wrong — blocks the event loop
def save_memory(key: str, content: str) -> str:
    conn = sqlite3.connect(db_path)
    conn.execute("INSERT ...", (key, content))
```

### Tools — Defensive error handling

Every tool MUST have `try/except` so failures return to the LLM as an observation, without crashing the graph:

```python
@tool
async def my_tool(input: str) -> str:
    """Clear description so the LLM knows when to use this."""
    try:
        result = await do_something(input)
        logger.info("my_tool completed", extra={"input": input[:50]})
        return result
    except Exception:
        logger.exception("my_tool failed", extra={"input": input[:50]})
        return "Error: tool failed. Check the logs."
```

### Imports — standard order (auto-sorted by ruff)

```python
# 1. stdlib
import asyncio
import logging
from pathlib import Path

# 2. third-party
from langchain.tools import tool
from pydantic import BaseModel
from rich.panel import Panel

# 3. local
from vectora.settings import settings
from vectora.services.security import is_safe_file_path
```

### Docstrings — only when they add value

```python
# ✅ Good — explains the non-obvious "why"
async def call_llm(state: State, config: RunnableConfig) -> dict:
    """Invoke LLM with sliding window history.

    Uses trim_messages with fallback to prevent 'contents are required'
    error when ToolMessage alone exceeds max_context_tokens.
    """

# ❌ Unnecessary — just restates the function name
async def call_llm(state: State, config: RunnableConfig) -> dict:
    """Call the LLM with the given state and config."""
```

---

## Project Structure

```
src/
├── agent.py          # AgentManager — main orchestrator
├── graph.py          # LangGraph graph builder
├── state.py          # TypedDict State
├── context.py        # Context schema
├── main.py           # CLI entry point
├── version.py        # Dynamic version via importlib.metadata
├── config/           # Settings (Pydantic), defaults.env
├── nodes/            # LangGraph nodes (engine, debug)
├── tools/            # 14 tools (fs, rag, web, memory, mcp)
├── mcp/              # MCP Server, Client, VectoraProxy
├── agents/           # Orchestrator + specialized agents + identity
├── services/         # Services (queue, memory, checkpoint, security...)
├── ui/               # TUI (chat, commands, setup wizard)
└── testing/          # Fixtures, mocks, message factories
```

---

## Git Workflow

### 1. Create a branch

```bash
git checkout main && git pull origin main
git checkout -b feat/my-feature
# or fix/bug-description, docs/update-readme, etc.
```

### 2. Commits — Conventional Commits (required)

```bash
git add src/tools/new_tool.py
git commit -m "feat: add new_tool for X"
```

Valid types:

- `feat:` — New feature
- `fix:` — Bug fix
- `docs:` — Documentation only
- `refactor:` — Code change with no behavior change
- `test:` — Tests
- `chore:` — Dependencies, build, config, CI

### 3. Pre-commit Hooks

Hooks run automatically on `git commit`:

```
Ruff Lint      → Python linting
Ruff Format    → consistent style
Prettier       → markdown and YAML
Bandit         → security scan
```

If a hook fails, fix the error, `git add` again, then re-commit:

```bash
uv run ruff check src/ --fix
uv run ruff format src/
git add src/
git commit -m "feat: my feature"
```

### 4. Pull Request

```bash
git push origin feat/my-feature
gh pr create --title "feat: my feature" --body "Description..."
```

---

## Adding a New Tool

1. Create in `src/tools/<category>.py` with the `@tool` decorator
2. Add to `src/tools/__init__.py` (imports + `__all__`)
3. Register in `src/mcp/server.py` as `@mcp.tool()` with a timeout
4. Update `src/settings.py` if a feature flag is needed
5. Write tests in `tests/unit/test_tools_<category>.py`
6. Update `docs/MVP_SCOPE.md` and `README.md`

---

## Adding a New LangGraph Node

1. Implement the node function in `src/nodes/engine.py`
2. Register in the builder in `src/graph.py` with `builder.add_node()`
3. Add edges (`add_edge` or `add_conditional_edges`)
4. Update `State` in `src/state.py` if the node needs a new field
5. Write tests in `tests/integration/test_graph_execution.py`

---

## Code of Conduct

- Respect in issues, PRs, and discussions
- Mistakes are learning opportunities, not a reason for judgment
- Ask before submitting large architectural changes
- Open an issue first to discuss significant features

Questions? Open an issue on GitHub.

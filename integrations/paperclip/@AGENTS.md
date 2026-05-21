# Integration Protocol: Paperclip ↔ Vectora

This document establishes the **official integration contract** between the **Paperclip** ecosystem (multi-agent framework) and **Vectora** (RAG + LangGraph hub). Required reading for any AI Agent or developer implementing connectors, plugins, or Vectora clients inside Paperclip.

The goal is to allow **N Paperclip agents** to share **a single Vectora server** (with a common LanceDB and singleton AgentManager), while maintaining **fully isolated sessions** via `thread_id`. There is no database duplication or copies of embeddings — just one central hub serving multiple clients concurrently.

---

## 1. Architectural Principles

The Paperclip → Vectora integration is governed by five non-negotiable principles that guarantee performance, isolation, and system stability.

### 1.1. Centralized Hub (Single Source of Truth)

There is **exactly one** active Vectora process per deployment. It acts as the **shared cognitive hub** for all Paperclip agents, exposing tools, resources, and A2A (Agent-to-Agent) delegation capability.

Vectora runs as a standalone Docker container (see `docker-compose.yml` in the project root). Multiple Paperclip agents connect to the same container — there is no Vectora per agent, and this is fundamental to avoiding LanceDB corruption and duplication of expensive embeddings.

### 1.2. Session by `thread_id`, NOT by Instance

Each Paperclip agent must have a unique, stable `thread_id` throughout its lifetime. This ID is the **cognitive segregation key** inside Vectora — the LangGraph Checkpointer uses `thread_id` to index memories, history, and state for each conversation inside **a single SQLite file**.

It is neither necessary nor permitted for each agent to have its own SQLite file. The Checkpointer pattern already guarantees that sessions with different `thread_id`s cannot see each other's history. Trying to create separate SQLite files is an antipattern and breaks the architecture.

### 1.3. "Dumb" Client, "Smart" Server

Paperclip acts as an **uninformed client**: it only sends tasks in natural language and the `thread_id`. All reasoning logic, tool decisions, RAG, and synthesis happen inside Vectora.

This separation of concerns prevents coupling — Paperclip does not need to know which tools exist, which LLM is running, or how RAG is executed. It simply trusts that Vectora will resolve the task.

### 1.4. Communication via MCP (Model Context Protocol)

All communication between Paperclip and Vectora **must** use the MCP protocol. Creating custom REST APIs, parallel gRPC, or any other protocol is not permitted. MCP provides typing, capability discovery, and standardized error handling.

The transport can be `stdio` (local, child process) or `sse` (HTTP, multi-container). The choice depends on the deployment, but the application protocol is always the same.

### 1.5. Async-First, Always

Every interaction with Vectora is I/O-bound (network, database, LLM). Therefore, **every Paperclip client must be implemented with `async/await`**. Synchronous calls would block the client agent's event loop and degrade overall system performance.

The `VectoraProxy` (official helper in `vectora/mcp/proxy.py`) already implements this pattern. Using it is the recommended integration approach.

---

## 2. Connection Modes

Vectora supports two MCP transports, selected via the `MCP_TRANSPORT` environment variable. The decision between them depends exclusively on the Paperclip deployment topology.

### 2.1. `stdio` Mode (Local)

Use this mode when Paperclip and Vectora run on the **same host** (no separate containers or network communication). Vectora is started as a child process of the Paperclip agent via `uv run vectora-mcp`.

This is the ideal mode for local development, unit tests, and scenarios where a single Paperclip agent needs Vectora exclusively. Latency is minimal (IPC via pipes), but there is no concurrency between agents — each Paperclip process would have its own Vectora child.

```python
from vectora.mcp import create_local_proxy

async with create_local_proxy() as vectora:
    result = await vectora.delegate(
        task="Summarize the latest PR from repo X",
        thread_id="paperclip_dev_machine_001",
    )
```

### 2.2. `sse` Mode (Remote Multi-Agent)

Use this mode when multiple Paperclip agents (in different containers, machines, or processes) need to share **a single Vectora**. This is the **canonical production mode** for the multi-agent scenario.

Vectora runs in its own Docker container, listening on `MCP_HOST:MCP_PORT` (default `0.0.0.0:8000`). Each Paperclip agent establishes its own HTTP/SSE connection, but all share the same LanceDB, AgentManager, and SQLite. Isolation between agents happens exclusively via `thread_id`.

```python
from vectora.mcp import create_remote_proxy

VECTORA_URL = "http://vectora.internal:8000/sse"

async with create_remote_proxy(VECTORA_URL) as vectora:
    result = await vectora.delegate(
        task="Analyze sentiment across the last 50 GitHub issues",
        thread_id=f"paperclip_agent_{agent_id}",
    )
```

### 2.3. Starting Vectora in Remote Mode

Transport configuration is done via environment variables in `docker-compose.yml`. Simply set `MCP_TRANSPORT=sse` in the Vectora project's `.env` and bring the container up.

```bash
# .env (Vectora project)
MCP_TRANSPORT=sse
MCP_HOST=0.0.0.0
MCP_PORT=8000

# Start the hub
docker compose up -d
```

After this, the endpoint `http://vectora:8000/sse` will be available to any Paperclip agent that needs to connect.

---

## 3. The `thread_id` Contract

The `thread_id` is the most important element of this protocol — it defines **who each agent is** inside Vectora. Errors in generating or using `thread_id` result in context leakage between agents or memory loss.

### 3.1. Recommended Format

Paperclip should generate `thread_id` in the format `paperclip_<agent_role>_<instance_id>`, where `<agent_role>` identifies the agent type (e.g., `summarizer`, `researcher`, `coder`) and `<instance_id>` is unique per instance (UUID, timestamp+random, or config hash).

This format makes debugging easier (Vectora logs show which agent made each call) and guarantees global uniqueness. Valid example: `paperclip_summarizer_a1b2c3d4`.

### 3.2. Stability During Agent Lifetime

The `thread_id` **must be persisted** by the Paperclip agent throughout its lifetime. If an agent restarts and generates a new `thread_id`, it will lose all conversation history stored in Vectora — effectively "amnesia".

It is recommended to store `thread_id` in the Paperclip agent's state (e.g., config file, local database, environment variable) and reuse it after restarts.

### 3.3. Integer Conversion Inside Vectora

Internally, Vectora currently uses `thread_id: int` in some APIs for LangGraph compatibility. `VectoraProxy.delegate()` handles this conversion automatically when it receives a numeric string, but pure alphanumeric IDs may cause an error.

Current workaround: use `hash(thread_id_str) & 0xFFFFFFFF` if you need a stable `int` from a string. Future roadmap: migrate all APIs to `thread_id: str` (open issue).

---

## 4. Available APIs via `VectoraProxy`

`VectoraProxy` exposes four families of operations covering 100% of a Paperclip agent's needs. Each has different semantics and cost — choosing the right operation for each task is critical for performance.

### 4.1. `delegate(task, thread_id)` — A2A Delegation

Use for **complex** tasks that require reasoning, multiple tools, or information synthesis. Vectora runs its full internal LangGraph, decides which tools to call, executes RAG/search/analysis, and returns the final result.

This is the most powerful operation, but also the most expensive (can take up to 5 minutes). Use when Paperclip cannot decompose the task into atomic calls, or when you want to delegate 100% of the problem-solving.

```python
result = await vectora.delegate(
    task="Research the 5 best RAG practices in 2025 and summarize in bullets",
    thread_id="paperclip_researcher_42",
)
```

### 4.2. `call_tool(name, args)` — Atomic Tool

Use when Paperclip **already knows** which tool to invoke. Much faster than `delegate()` because it does not run the full LangGraph — it only executes the tool directly.

This is the preferred operation when the Paperclip agent has its own decision logic and only needs to execute a specific operation (e.g., read a file, run a vector search, index a document).

```python
docs = await vectora.call_tool(
    "vector_search_tool",
    {"query": "RAG patterns", "collection": "docs", "limit": 5},
)
```

### 4.3. `get_thread_context(thread_id)` / `get_thread_history(thread_id)` — Resources

Use to **inspect session state** without invoking the LLM. Returns metadata, summary, and recent messages — useful for debugging, dashboards, or for the Paperclip agent to decide if it already has enough context.

This operation is practically free (direct SQLite read) and idempotent. Can be called frequently without impacting the server.

```python
context = await vectora.get_thread_context("paperclip_agent_42")
print(f"Messages in this session: {context['message_count']}")
```

### 4.4. `list_tools()` — Capability Discovery

Use at Paperclip agent initialization to **dynamically discover** which tools Vectora exposes. This allows the client to adapt to new Vectora versions without code changes.

Do not call this API on every operation — the result is stable within a session. Cache it at startup and revalidate only if a "tool not found" error occurs.

```python
tools = await vectora.list_tools()
for tool in tools:
    print(f"- {tool['name']}: {tool['description']}")
```

---

## 5. Usage Patterns (Recipes)

Below are recommended patterns for common Paperclip scenarios. Use them as a starting point and adapt to your agent's needs.

### 5.1. Persistent Agent with Memory

Scenario: a Paperclip agent that maintains long-term memory across executions (e.g., personal assistant, code reviewer with history).

The agent should use a stable `thread_id` stored in local state, open the connection at initialization, and maintain it for the entire session. Memories are automatically persisted by the Vectora Checkpointer.

```python
class PersistentPaperclipAgent:
    def __init__(self, agent_id: str, vectora_url: str):
        self.thread_id = f"paperclip_persistent_{agent_id}"
        self.vectora_url = vectora_url
        self._proxy = None

    async def __aenter__(self):
        from vectora.mcp import create_remote_proxy
        self._proxy = create_remote_proxy(self.vectora_url)
        await self._proxy.connect()
        return self

    async def __aexit__(self, *args):
        await self._proxy.disconnect()

    async def ask(self, question: str) -> str:
        return await self._proxy.delegate(
            task=question,
            thread_id=self.thread_id,
        )
```

### 5.2. Concurrent Agent Pool

Scenario: multiple Paperclip agents running in parallel, each processing an independent task queue.

Each agent in the pool must have its own unique `thread_id`. Connections can be created on demand (short-lived) or kept in a pool (long-lived) depending on traffic patterns.

```python
import asyncio
from vectora.mcp import create_remote_proxy

async def process_task(agent_id: int, task: str):
    async with create_remote_proxy("http://vectora:8000/sse") as vectora:
        return await vectora.delegate(
            task=task,
            thread_id=f"paperclip_worker_{agent_id}",
        )

# 10 agents in parallel, each with its own isolated session
results = await asyncio.gather(*[
    process_task(i, f"Task {i}") for i in range(10)
])
```

### 5.3. Hybrid Agent (call_tool + delegate)

Scenario: a sophisticated Paperclip agent with its own decision logic that delegates heavy tasks to Vectora.

Use `call_tool()` for operations Paperclip already knows how to execute, and `delegate()` only when the task requires reasoning it cannot (or does not want to) do locally.

```python
async with create_remote_proxy(VECTORA_URL) as vectora:
    # Paperclip decides to search RAG first (atomic operation)
    docs = await vectora.call_tool(
        "vector_search_tool",
        {"query": user_question, "limit": 5},
    )

    if not enough_context(docs):
        # No local context — delegate full analysis to Vectora
        answer = await vectora.delegate(
            task=f"Answer: {user_question}. Run a web search if needed.",
            thread_id=session_id,
        )
    else:
        # Has context — Paperclip processes locally
        answer = local_llm.generate(user_question, docs)
```

---

## 6. Error Handling

Errors in the Paperclip → Vectora integration must be handled defensively. `VectoraProxy` raises `VectoraProxyError` for all protocol failures, and it is up to the Paperclip agent to decide between retry, fallback, or propagation.

### 6.1. Timeouts

Vectora applies timeouts in layers: each individual tool has its own limit (10–120 s), and A2A delegation has a global timeout of 300 s (5 minutes). When these limits are exceeded, the returned response already contains the formatted error message — no exception is raised.

The Paperclip agent should always check whether the result starts with `"Error:"` to detect timeouts and decide whether to retry with a simplified task. Do not catch `TimeoutError` at the proxy layer — it is already handled internally by Vectora.

### 6.2. Connection Failures

Network errors (server offline, DNS, etc.) raise `VectoraProxyError` during `proxy.connect()`. The Paperclip agent should implement exponential retry and, if the error persists, log clearly and temporarily disable the integration.

Do not attempt to reconnect inside the same `async with` block — destroy the proxy and create a new one on the next attempt. The internal `AsyncExitStack` guarantees correct resource cleanup.

### 6.3. Response Validation

Even when there is no error, validate the response content before using it. Vectora may return messages like `"Error: Tool 'X' exceeded timeout..."` even under HTTP 200 (these are application errors, not protocol errors).

The rule is: always treat the returned string as untrusted input. If the Paperclip agent expects JSON, parse with `try/except`. If it expects text, check that it does not begin with known error prefixes.

---

## 7. Observability

Multi-agent operation is only manageable if there is visibility into what each agent is doing. Vectora already emits structured logs, and Paperclip should complement them with `thread_id` correlation.

### 7.1. Vectora Logs

All Vectora logs go to `~/.vectora/logs/mcp.log` (inside the container, mapped to a volume). Each entry includes the `thread_id` in `extra`, allowing filtering of logs by specific Paperclip agent.

To follow logs in real time:

```bash
docker compose logs -f vectora
# or
docker exec vectora tail -f /root/.vectora/logs/mcp.log
```

### 7.2. Recommended Metrics in Paperclip

The Paperclip agent should emit its own metrics for each Vectora interaction — at minimum: call latency, payload size, error rate, and operation type (`delegate` vs `call_tool`).

These metrics, combined with Vectora logs, make it possible to identify bottlenecks (e.g., a specific agent making too many unnecessary `delegate()` calls) and take corrective action.

### 7.3. LangSmith (Optional)

If the `LANGSMITH_API_KEY` variable is configured in Vectora, all internal LangGraph executions are automatically traced in LangSmith. This provides **full traces** of every delegation — useful for debugging unexpected agent behavior.

Paperclip does not need to configure anything to use this; simply check the LangSmith dashboard filtered by `thread_id`.

---

## 8. Integration Roadmap

This section lists planned improvements to the Paperclip ↔ Vectora integration, in priority order. Contributions and issues are welcome in the Vectora repository.

### 8.1. Official Paperclip Plugin (Future)

Next step: create a native Paperclip plugin in this same folder (`integrations/paperclip/plugin/`). The plugin will abstract `VectoraProxy` configuration, provide high-level decorators, and expose an ergonomic API following Paperclip conventions.

No ETA — depends on the maturity of the Paperclip plugin system and feedback from the first `VectoraProxy` users.

### 8.2. Native `thread_id: str`

Currently, alphanumeric IDs require a workaround (`hash`). Migration to native `str` is planned and will simplify `thread_id` generation in Paperclip — just concatenate strings without worrying about conversions.

### 8.3. Response Streaming

Today, `delegate()` returns the complete response after LangGraph finishes (can take minutes). SSE streaming will allow Paperclip to receive the response in real time, improving UX and detecting hangs earlier.

### 8.4. Health Check and Auto-Discovery

Adding a `/health` endpoint to Vectora SSE allows orchestrators (Kubernetes, Docker Swarm) to perform real health checks. Combined with mDNS or a service registry, Paperclip agents can automatically discover the Vectora endpoint without hardcoding.

---

## 9. References

Related documentation for deeper technical understanding of the components referenced in this protocol.

- **Vectora** — MCP server source: `vectora/mcp/server.py`
- **VectoraProxy** — Official client: `vectora/mcp/proxy.py`
- **A2A Tests** — Validation suite: `tests/integration/test_a2a_integration.py`
- **MCP Protocol** — Official specification: https://modelcontextprotocol.io
- **LangGraph Checkpointer** — Persistence pattern: https://langchain-ai.github.io/langgraph/concepts/persistence/
- **Vectora AGENTS.md** — General development rules: `/AGENTS.md`

---

## 10. Changelog

Every change to this document must be versioned with a `docs:` commit following Conventional Commits, as per the project's `AGENTS.md` rules.

- **v1.1.0** (2026-05-20) — Translated to English. Aligned with README: updated prerequisites (Cohere + Tavily required), LLM provider table, PyPI install name (`vectora-agent`), and `vectora-mcp` CLI reference.
- **v1.0.0** (2026-05-17) — Initial version. Establishes multi-agent architecture, `thread_id` contract, `stdio`/`sse` modes, and `VectoraProxy` API.

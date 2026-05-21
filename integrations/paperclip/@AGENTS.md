# Integration: Paperclip ↔ Vectora

This document describes how to connect a **Paperclip** instance to a **Vectora** MCP server, both running as separate Docker containers — typically on the same VPS behind a shared Traefik reverse proxy.

---

## Architecture

```
[Paperclip container]  ──HTTPS/SSE──▶  [Vectora container]
  ghcr.io/hostinger/hvps-paperclip        ghcr.io/brunosrz/vectora
  paperclip.yourdomain.com                vectora.yourdomain.com/sse
```

Both containers are independent stacks. They communicate via the public HTTPS endpoint exposed by Traefik — there is no shared Docker network required. The Vectora container serves as the **shared cognitive hub**: one instance, shared LanceDB and SQLite, sessions isolated by `thread_id`.

---

## Deploy

### 1. Start Vectora

From the Vectora project root, with `VECTORA_DOMAIN` and `ACME_EMAIL` set in `.env`:

```bash
docker compose -f docker-compose.yml -f docker-compose.traefik.yml up -d
# Vectora SSE endpoint: https://vectora.yourdomain.com/sse
```

### 2. Start Paperclip

From the `integrations/paperclip/` folder, with the variables below set in `.env`:

```bash
docker compose -f docker-compose.paperclip.yml up -d
```

Required `.env` variables for Paperclip:

```env
COMPOSE_PROJECT_NAME=paperclip
TRAEFIK_HOST=yourdomain.com
VPS_IP=your.vps.ip
PUBLIC_PORT=3100

# Vectora endpoint — set after Vectora is running
VECTORA_SSE_URL=https://vectora.yourdomain.com/sse
```

Add `VECTORA_SSE_URL` to the Paperclip container environment so agents can read it at runtime.

---

## Connecting from a Paperclip Agent

Use `VectoraProxy` from `vectora.mcp.proxy`:

```python
from vectora.mcp.proxy import create_remote_proxy

VECTORA_URL = os.environ["VECTORA_SSE_URL"]  # https://vectora.yourdomain.com/sse

async with create_remote_proxy(VECTORA_URL) as vectora:
    result = await vectora.delegate(
        task="Summarize the last 5 PRs from repo X",
        thread_id="paperclip_agent_001",
    )
```

### `thread_id` rules

- Each agent instance must use a **unique, stable** `thread_id` across restarts
- Format: `paperclip_<role>_<instance_id>` — e.g. `paperclip_researcher_a1b2c3`
- Never share the same `thread_id` between concurrent agents
- Persist `thread_id` in the agent's own state — losing it means losing conversation history

### Available operations

| Method                          | Use when                                                   |
| ------------------------------- | ---------------------------------------------------------- |
| `delegate(task, thread_id)`     | Complex task — let Vectora reason, pick tools, synthesize  |
| `call_tool(name, args)`         | You know exactly which tool to call (faster, no LangGraph) |
| `get_thread_context(thread_id)` | Inspect session state without invoking the LLM             |
| `list_tools()`                  | Discover available tools at startup (cache the result)     |

---

## Observability

Vectora logs go to `~/.vectora/logs/mcp.log` inside the container:

```bash
docker compose -f docker-compose.yml logs -f vectora
```

If `LANGSMITH_API_KEY` is set in Vectora's `.env`, every delegation is fully traced in LangSmith — filter by `thread_id` to see exactly what each Paperclip agent triggered.

---

## References

- Vectora MCP server: `vectora/mcp/server.py`
- VectoraProxy client: `vectora/mcp/proxy.py`
- Vectora Docker deploy: `docker-compose.yml` + `docker-compose.traefik.yml`
- MCP Protocol spec: https://modelcontextprotocol.io

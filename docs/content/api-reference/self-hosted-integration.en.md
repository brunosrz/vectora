---
title: Self-Hosted Integration (Internal API)
weight: 6
---

Everything documented in [Overview](../overview), [Classify](../classify), [Extract](../extract), and [Jobs](../jobs) is the **public, stable** `/v1/*` API. This page documents something different: the **internal API** — the same set of endpoints the Vectora frontend itself calls against your own self-hosted instance.

It's real, it works, and it's what powers the chat UI, RAG, gateways, and settings. But it's **not a stable public contract** — endpoint shapes can change between releases without a deprecation notice, the way any frontend-internal API does. Use it for your own scripts, dashboards, or automations against *your own* Vectora instance, not for building a product that ships to other people's servers (for that, wait for the `/v1/*` endpoints on the [roadmap](../roadmap)).

## Authentication

Two ways to authenticate, both accepted by every endpoint below (`get_current_user` dependency, `backend/api/middleware/auth.py`):

1. **Cookie** — what the frontend uses. `POST /auth/signin` sets an httpOnly `vectora_access` cookie; every subsequent request from the same browser session is authenticated automatically.
2. **Bearer token** — what you want for scripts. `POST /auth/signin` also returns `access_token`/`refresh_token` in the response body; send it as `Authorization: Bearer <access_token>` on every request.

```bash
# Sign in, capture the access token
TOKEN=$(curl -s -X POST http://localhost:8080/auth/signin \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"..."}' | jq -r .access_token)

# Use it on any endpoint below
curl -s http://localhost:8080/auth/me -H "Authorization: Bearer $TOKEN"
```

Access tokens expire; call `POST /auth/refresh` with the `refresh_token` to get a new pair without asking for the password again.

## Full schema: use the Swagger UI

This page gives you 1-2 examples per area — for the exact request/response shape of every field, the source of truth is the auto-generated OpenAPI spec (same one behind [Overview](../overview)'s `/docs` link):

```text
GET /docs           # interactive Swagger UI — try requests right from the browser
GET /openapi.json   # raw spec, for generating a client
```

## By area

### `/auth/*` — accounts, settings, envs

- `POST /auth/signin` / `POST /auth/signup` — see above.
- `GET /auth/me` — current user profile.
- `GET /auth/envs` / `POST /auth/envs` / `DELETE /auth/envs/{key}` — read/write environment-backed settings (API keys, provider config) that don't have a dedicated endpoint yet.

### `/chat/*` — streaming chat (SSE)

Chat doesn't live at a plain `/chat` path — it's `POST /vectora.chat.v1.ChatService/StreamChat`, returning a Server-Sent Events stream (each event is a typed JSON packet: token deltas, tool calls, thread metadata). Leave `thread_id` empty to start a new conversation; the first event of the stream carries the generated `thread_id` to reuse on the next call.

```bash
curl -N -X POST http://localhost:8080/vectora.chat.v1.ChatService/StreamChat \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"thread_id":"","message":"hello","config":{"chat_mode":true}}'
```

### `/rag/*` — retrieval settings and collections

- `GET /rag/settings` / `PATCH /rag/settings` — reranker on/off + top_k, embedding/rerank provider (`auto`/`cohere`/`voyage`/`ollama`/`openrouter`), file types to ingest.
- `GET /rag/collections` / `DELETE /rag/collections/{name}` — list/drop indexed collections.
- `POST /rag/search` — direct retrieval, same `vector_search` the agent uses internally.

### `/gateways/*` — Ollama and OpenRouter

- `GET /gateways/ollama/models` — discovers models installed on the configured Ollama host (`{OLLAMA_BASE_URL}/api/tags`); `reachable: false` if the host is down, never a 500.
- `GET /gateways/openrouter/models?q=` — searches OpenRouter's public catalog (cached ~1h server-side).
- `POST /gateways/{ollama,openrouter}/registered` — registers a discovered model so it shows up in `GET /models/providers`.

### `/models/providers` — the aggregated model catalog

Merges the static provider catalog (Gemini, OpenAI, Anthropic, Cohere) with whatever you've registered via the gateways above — this is what feeds the model selector in the chat UI.

### `/mcp` — not REST

If you're integrating an MCP-aware client (Claude Code, Claude Desktop, Cursor) rather than writing raw HTTP calls, `/mcp` speaks the MCP protocol, not REST — see [Connecting MCP Clients](../../guides/mcp-clients) instead.

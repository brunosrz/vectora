---
title: Roadmap
weight: 5
---

To be transparent about what exists today versus what's planned:

## ✓ Available today

- `POST /v1/classify`
- `POST /v1/extract`
- `POST /v1/jobs` + `GET /v1/jobs/{id}/events` (SSE)
- Automatic OpenAPI docs at `/docs` and `/openapi.json`

## 📋 Planned, not implemented

- **Dedicated API authentication** — OAuth2 client credentials for server-to-server use (today the `/v1/*` endpoints are public, differentiated only by rate limit).
- **Chat/documents/projects endpoints via API** — today chat is only accessible via the frontend's internal SSE, MCP, or the CLI; there's no public `/v1/chat` or `/v1/documents` yet.
- **Official SDKs** — `pip install vectora-sdk` (Python) and `@vectora/sdk` (TypeScript) don't exist yet.
- **Outbound webhooks** (Vectora → external systems) — today Vectora only receives third-party webhooks (GitHub/GitLab/Slack) for background tasks, it doesn't emit its own.
- **OpenAI API compatibility** — would let existing OpenAI SDKs point at Vectora; not implemented yet.

If you depend on any of these features, [open an issue](https://github.com/vectora-company/vectora/issues) or reach out via [support](https://vectora.company/support) — it helps prioritize the roadmap.

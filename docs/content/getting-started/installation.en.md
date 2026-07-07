---
title: Installation
weight: 2
---

Vectora ships as a **native desktop app** (Electron + a compiled Python backend) for Windows, macOS, and Linux, with built-in auto-update. There is no "single Docker image" of the product — Docker, when used, only spins up optional infrastructure (Postgres/Redis/Qdrant for complete mode), never Vectora itself.

## Option 1 — Native installer (recommended)

Download the installer for your OS:

| OS      | Format                                   | Signing                                |
| ------- | ---------------------------------------- | -------------------------------------- |
| Windows | `.msi` or `.exe` (NSIS)                  | EV certificate (Azure Trusted Signing) |
| macOS   | `.dmg` (Apple Silicon only)              | Apple Developer ID + notarized         |
| Linux   | `.AppImage`, `.deb`, or `.rpm`           | unsigned                               |

Install normally (double-click / `dpkg -i` / `rpm -i`). The app opens with the backend already embedded — no separate Python, Node, or any other dependency to install.

Future updates arrive automatically via auto-update (served by `updates.vectora.company`).

## Option 2 — From source (dev)

To contribute or run in development mode:

**Requirements**: Python 3.13, [uv](https://docs.astral.sh/uv/), Node.js 24+, `pnpm`.

```bash
git clone https://github.com/vectora-company/vectora.git
cd vectora/vectora

uv sync                          # Python dependencies
pnpm --dir frontend install       # frontend dependencies

cp .env.example .env
# edit .env: GOOGLE_API_KEY (or another provider), COHERE_API_KEY, TAVILY_API_KEY
```

Two terminal windows:

```bash
# Terminal 1 — full backend + MCP (/mcp) + SPA (port 8080)
uv run vectora start --port 8080

# Terminal 2 — frontend dev server (Vite, port 3000, proxies to the API)
pnpm --dir frontend dev
```

Open `http://localhost:3000`. The first user to sign up becomes the root administrator.

## Required API keys

| Key                                                                  | Required?    | For                                       |
| -------------------------------------------------------------------- | ------------ | ----------------------------------------- |
| An LLM provider (Gemini, OpenAI, Anthropic, Cohere, or local Ollama) | Yes          | Chat, code generation, response synthesis |
| `COHERE_API_KEY` (or VoyageAI)                                       | Yes, for RAG | Embeddings + reranking                    |
| `TAVILY_API_KEY`                                                     | Optional     | Web search                                |

The model selector in chat only shows providers with a configured key — no key, no provider in the list.

## License

The app works **without a license** in Free mode (100% local). To unlock Pro features (multi-user web chat, complete storage, webhooks, REST API with a higher rate limit), you need a `VECTORA_TOKEN`, obtained from the [dashboard](https://vectora.company/dashboard) after subscribing to a paid plan.

## Next step

→ [Quick start](../quick-start)

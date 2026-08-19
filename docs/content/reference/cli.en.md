---
title: CLI Reference
weight: 1
---

```text
vectora [command] [options]
```

## Commands

| Command            | What it does                                                           |
| ------------------ | ---------------------------------------------------------------------- |
| _(no args)_        | prints help                                                            |
| `start`            | starts the full backend + the SPA (fullstack)                         |
| `start --headless` | starts without opening a window (backend + tray)                       |
| `config`           | shows/edits settings; subcommands: `keys`, `docker`, `qdrant`, `redis` |
| `storage`          | migrations, diagnostics, backup/restore, BaaS wizard                   |
| `sessions`         | lists all saved sessions                                               |

## `start` options

| Option                                   | Default   | Description                                        |
| ---------------------------------------- | --------- | -------------------------------------------------- |
| `--headless`                             | —         | doesn't open a window (keeps backend + MCP + tray) |
| `--host <host>`                          | `0.0.0.0` | listen host                                        |
| `--port <n>`                             | `8080`    | port                                               |
| `--ssl-certfile` / `--ssl-keyfile <pem>` | —         | serve over `https://`                              |

## `vectora config`

```bash
vectora config keys         # interactive wizard for API keys + LLM provider
vectora config docker up    # spins up local Postgres + Redis + Qdrant (Docker)
vectora config qdrant       # Qdrant-specific config
vectora config redis        # Redis-specific config
```

## `vectora storage`

```bash
vectora storage wizard                       # managed infra wizard (Supabase/Neon/Qdrant Cloud/self-hosted)
vectora storage migrate status               # applied/pending migrations
vectora storage migrate upgrade              # applies pending migrations
vectora storage migrate to-postgres          # SQLite → Postgres
vectora storage migrate to-qdrant <collection> # LanceDB → Qdrant
vectora storage migrate to-pgvector          # LanceDB → pgvector
vectora storage migrate memory-to-native     # old memories → native store
```

See [Storage: lite vs. complete](../../concepts/storage) for the full context.

## `vectora sessions`

```bash
vectora sessions
```

Lists all locally saved sessions (threads).

## Typical usage on a VPS over SSH

The frontend covers day-to-day configuration, but on a headless server the CLI exposes the essentials:

```bash
uv run vectora config keys         # configure API keys
uv run vectora config docker up    # spin up optional infrastructure
uv run vectora start --headless    # backend + MCP, no window
```

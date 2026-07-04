---
title: Backup & Restore
weight: 4
---

## What to back up

Everything relevant lives in `~/.vectora/`:

```text
~/.vectora/
├── config.toml
├── auth.key
├── data/               # vectora.db, embedding_queue.db, traces.db, lancedb/
├── artifacts/
├── secrets/            # KeePassXC vaults
├── skills/
├── safe_roots.json
└── workspaces.json
```

Simple backup: archive all of `~/.vectora/` (minus caches, if you've identified any temporary cache directory).

## Complete mode

If you're in complete mode, backing up RAG/checkpoint/cache data is your managed provider's responsibility (Supabase, Neon, Qdrant Cloud) or your own Postgres/Qdrant/Redis backup routine — Vectora doesn't automatically back up those external services for you.

## Restoring

Stop Vectora, restore the contents of `~/.vectora/` (or the managed database backup, if applicable), start Vectora again. There's no dedicated "restore" CLI command today — it's a file/infra operation, not a product feature.

## Migrating between storage modes

To move data between lite and complete (not the same thing as backup/restore), see the `vectora storage migrate` commands in [Storage: lite vs. complete](../../concepts/storage).

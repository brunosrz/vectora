---
title: Updates
weight: 5
---

## How it works today

The desktop app uses `electron-updater`, checking for new versions against the `services.vectora.company` worker (`GET /updates/:channel/:os/:arch/latest.yml`). Downloading and installing the update happens automatically in the background.

## Version quarantine

If a new version shows a crash rate above a threshold within a short window (via update telemetry), the worker moves that version to a quarantine list and starts serving `previous_stable` again for new checks — this doesn't undo installations already made, but it contains the blast radius for anyone who hasn't updated yet.

## Update channel

Binaries and the manifest (`latest.yml`, the `electron-updater` standard) live in R2, served by the worker's `/updates/*` and `/download/*` routes — the same worker that covers the company's auth/billing/license.

## Roadmap: changelog + manual approval + rollback

A more explicit flow (see the changelog before downloading, manually approve installation, automatic backup before applying, real rollback to a previous version) is designed but **not yet implemented** — current behavior is auto-update with no visible changelog and no manual approval. This is roadmap, not an available feature today.

## When developing from source

Running via `uv run vectora start`, there's no auto-update — you update with `git pull` + `uv sync` as usual.

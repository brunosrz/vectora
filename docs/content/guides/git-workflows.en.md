---
title: Git Workflows
weight: 4
---

The `coder` subagent has 14 native git operations, available both in chat (natural language) and in the workbench's **Diff (Git)** tab (direct UI).

## In chat

Ask in natural language:

```text
Commit these changes with a descriptive message
```

```text
Create a new branch from main and check it out
```

Commits and pushes are destructive actions — they go through HITL unless the active permission mode is "Autonomous". See [Orchestrator & Subagents](../../concepts/sub-agents).

## In the workbench

The **Diff (Git)** tab has two views:

- **Changes** — modified/staged/untracked files with inline diff; stage/unstage per file or per hunk.
- **History** — commit log; clicking a commit shows that commit's full diff.

Dedicated modals cover **Stash** (temporarily shelving changes), **Worktrees** (multiple branches checked out in parallel), and **PR creation** (via the `gh` CLI, if available on the system).

## Prerequisite

The workspace needs to be **trusted** (see [First workspace](../../getting-started/first-workspace)) — state-changing git operations don't run in an untrusted workspace.

## `gh` CLI

GitHub operations (creating a PR, commenting on an issue, reviewing) use the `gh` CLI installed on your system, reusing the authentication you already have (`gh auth login`) — Vectora doesn't ask for a separate GitHub token.

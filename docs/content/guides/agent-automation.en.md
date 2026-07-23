---
title: Agent Automation
weight: 6
---

Beyond answering in the current turn, Vectora's agent can delegate work to isolated subagents, schedule work for later, learn reusable patterns from a session, and (in a limited, scaffolded form today) receive messages from outside the chat UI.

## Delegate — isolated subagent execution

When the orchestrator delegates a coding task to the `coder` subagent, it can run that work in an isolated **git worktree** rather than directly in your main workspace checkout. This means a long-running or exploratory change doesn't collide with files you're actively editing yourself, and can be reviewed or discarded as its own branch before merging. Worktree creation reuses the same git logic the `git_worktree` tool already exposes, so it fails the same honest way (invalid branch, non-git workspace, disk full) rather than leaving a task stuck.

## Schedule — recurring tasks and one-off subagent runs

The agent can schedule work in two shapes:

- **Recurring tasks** (`schedule_task`) — described in plain-language time expressions ("every day at 9am", "every Friday at 6pm", "every 2 hours"), parsed deterministically into a cron schedule. An expression that doesn't match a known pattern is never guessed — it comes back as an error asking you to rephrase.
- **One-shot subagent runs** (`schedule_subagent_task`) — schedules a *specific* subagent (`coder` or `search`), not the full orchestrator, to run once at a future time ("in 30 minutes", "in 2 hours"). A scheduled `coder` run uses the same worktree isolation as Delegate above when a workspace is active.

Both surface in the Tasks tab of the workbench, distinguishing scheduled runs from work happening in the current turn.

## Remember — automatic learning, always with approval

Every 5 turns of a conversation, Vectora automatically reviews the transcript for reusable patterns — skills worth saving, facts worth remembering — and, if it finds anything, proposes them the next time you interact with that thread. Nothing is written automatically: the proposal sits pending until you approve or reject it, and a pending proposal blocks a new automatic trigger until it's resolved (so it doesn't queue up repeated proposals).

You can also trigger this manually, or have the agent save a specific fact or install a specific skill directly — both of those actions require your approval the same way, and both leave a visible artifact in the **Plan tab** once approved, so what Vectora learned about your project stays visible and consultable, not just a diff that scrolls away.

## Vectora Connect — status

Vectora Connect is the interface for delivering chat messages through platforms other than the built-in UI (Telegram, Discord, WhatsApp, etc.), following the "Connect" concept from Hermes Agent. Today, this exists as a **generic scaffolding layer only**: message envelopes and thread-resolution plumbing that any platform adapter could plug into — but no concrete platform (Telegram or otherwise) is wired in yet. If you're evaluating Vectora for multi-platform messaging today, treat this as a planned capability, not a working integration.

## See also

- [Sessions & Workspaces](../../concepts/sessions-and-workspaces) — what a workspace is and how trust works
- [AI Jail](../../concepts/ai-jail) — sandboxing terminal/file access per workspace
- [Using the Workbench](../using-the-workbench) — the Tasks and Plan tabs in practice

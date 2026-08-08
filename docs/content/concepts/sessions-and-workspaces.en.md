---
title: Sessions & Workspaces
weight: 6
---

Two independent axes shape how a conversation behaves: **Chat vs Dev mode** (what the agent can do) and **Assistant vs IDE mode** (how the workbench is laid out). Understanding both makes it clear why a session sometimes has a workspace and sometimes doesn't, and why switching modes opens a new conversation.

## Chat mode vs Dev mode

- **Chat mode** — a lightweight conversational session with no filesystem, terminal, or git access. The agent still has web search, RAG, memory, and external integrations (Slack, Linear, Notion, etc.), just no workspace tools and no subagent delegation. There's nothing to trust here, so no workspace is created.
- **Dev mode** — the full agent: filesystem, terminal, git, browser, Context Graph, Library, scheduling — everything covered in [Agent automation](../../guides/agent-automation) and elsewhere in these docs. A Dev-mode session always has a workspace.

Switching between the two always starts a **new, empty thread** — Chat and Dev sessions are separate pools, not two views of the same conversation. This is a deliberate boundary, not a limitation to work around: a Chat session's history never silently gains file/terminal access just by flipping a switch.

## What a workspace is

A workspace is a folder on disk that the backend has been given permission to read and write. Internally, its `workspace_id` is derived deterministically from the folder's absolute path, and the registry (persisted locally) tracks trust state per folder.

**Trust** is what gates destructive tools (`file_write`, `terminal`, git operations): a workspace must be explicitly trusted before the agent can touch it.

- The folder the backend was **launched from** is auto-trusted — if you already have a shell there, you already have full control, so asking for confirmation would be theater.
- Any other folder you add later (via the workspace picker) requires an explicit trust confirmation dialog before the agent gets write access.

When you start a Dev-mode session without picking an existing folder, Vectora creates a dedicated, auto-trusted workspace for that thread under your Documents folder — materialized on disk only when the agent actually needs to write something, not eagerly on session start.

## Assistant mode vs IDE mode

Independent of Chat/Dev, the workbench itself has two layouts, toggled from the header (only visible inside an active Dev-mode session):

- **Assistant mode** — the chat is the primary surface; the workbench (files, terminal, diff, etc.) opens as a side panel.
- **IDE mode** — a docked, multi-tab code-editor layout takes over the main area, with chat alongside it — closer to a traditional IDE window.

This toggle only affects layout, not capability: the same tools and the same workspace are available in both.

## See also

- [Sandbox](../sandbox) — how a workspace's terminal/file access can be sandboxed
- [Using the Workbench](../../guides/using-the-workbench) — the tabs available in a Dev-mode session
- [Agent automation](../../guides/agent-automation) — Delegate, Schedule, Remember, Connect

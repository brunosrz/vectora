---
title: Agents Reference
weight: 4
---

The agent is built on the native engine (`backend/engine/conversation_loop.py::run_conversation`) — a supervisor (orchestrator) with two subagents.

## orchestrator

The single supervisor, entry point for every message. Decides whether to answer directly or delegate via the native `delegate_to_subagent` tool. Its own tools: `create_artifact`, `save_memory`, `get_memory`, `delete_memory`, plus access to RAG tools to answer simple questions about already-indexed content without delegating.

## coder

Specialist in filesystem, terminal, and git. Receives explicit instructions from the orchestrator (doesn't decide on its own what to do — executes what was delegated). Tools: `file_read`, `file_edit`, `file_write`, `grep`, `list_dir`, `terminal`, all 14 git operations, plus memory and RAG access.

## search

Specialist in real-time web search and RAG. Tools: `web_search`, `web_fetch`, `vector_search`, `embedding`, `ingest_docs`, plus memory. There's no separate third subagent dedicated only to RAG — that responsibility belongs to `search`.

## Middleware

- **HITL** (`HumanInTheLoopMiddleware`) — pauses before destructive tool calls, with behavior configurable by [permission mode](../../guides/using-the-chat#permission-modes).
- **Context** — every invocation carries `user_id`, `workspace_id`, and `permission_mode` via a typed `context_schema`.

## Checkpointer

`AsyncSqliteSaver` (lite mode) or a Postgres equivalent (complete mode) — persists graph state per thread, letting you resume a conversation exactly where it left off.

## See also

- [Orchestrator & Subagents](../../concepts/sub-agents) — conceptual overview
- [Tools reference](../tools) — full inventory

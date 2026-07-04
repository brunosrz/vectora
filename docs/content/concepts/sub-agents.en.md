---
title: Orchestrator & Subagents
weight: 3
---

Vectora's agent is built on `create_deep_agent` (LangGraph + [deepagents](https://github.com/langchain-ai/deepagents)) — not a hand-rolled orchestrator-by-nodes. This gives access to native middleware (configurable HITL), pluggable filesystem backends, and a supervisor that delegates to specialized subagents via an internal `task` tool.

## Orchestrator

The supervisor decides, on every turn: answer directly (simple questions, general conversation) or delegate to a subagent with an explicit instruction. There's no unnecessary routing hop — if the question doesn't need a file, terminal, or search, the orchestrator answers right away.

## The two subagents

| Subagent   | Specialty                                              | Main tools                                                                        |
| ---------- | ------------------------------------------------------ | --------------------------------------------------------------------------------- |
| **coder**  | Filesystem, terminal, git — code generation and review | `file_read`, `file_edit`, `file_write`, `grep`, `list_dir`, `terminal`, git tools |
| **search** | Real-time web search + RAG                             | `web_search`, `web_fetch`, `vector_search`, `embedding`, `ingest_docs`            |

There's no separate third subagent dedicated to RAG — context retrieval is a `search` responsibility, not its own subagent.

## HITL (Human-in-the-Loop)

Before any destructive action (writing a file, running a terminal command, `git push`), the graph **pauses** and asks for your approval — via the harness's native `HumanInTheLoopMiddleware`, not a raw `interrupt()`. Behavior changes based on the active **permission mode**:

| Mode         | Behavior                                                 |
| ------------ | -------------------------------------------------------- |
| Always ask   | every destructive action pauses                          |
| Accept edits | file edits go straight through; terminal/git still pause |
| Autonomous   | nothing pauses (advanced/trusted use)                    |
| Plan         | the agent only plans, never executes                     |

## Why this matters in practice

You don't have to blindly trust the agent: every tool call is traceable, every risky action goes through you before happening, and the "answer directly vs. delegate" decision is visible in the UI (the chat's "thinking" block shows the orchestrator's reasoning).

## See also

- [Using the chat](../../guides/using-the-chat) — permission modes in practice
- [Agents reference](../../reference/agents) — full subagent specs

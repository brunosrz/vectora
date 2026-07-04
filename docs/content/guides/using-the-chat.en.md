---
title: Using the Chat
weight: 1
---

## Sending messages

The chat input accepts text, drag-and-dropped files, pasted clipboard images, and file `@mentions` to bring specific content into context without having to describe it.

## Model selector

Only shows providers with a configured API key — Google Gemini, OpenAI, Anthropic, Cohere, or local Ollama. Switching models mid-conversation doesn't lose history.

## Permission modes

Control how automatically the agent acts before asking for your approval:

| Mode             | The agent...                                                              |
| ---------------- | ------------------------------------------------------------------------- |
| **Always ask**   | pauses before any destructive action (writing a file, terminal, git push) |
| **Accept edits** | applies file edits directly; terminal and git still pause                 |
| **Autonomous**   | doesn't pause for anything — use with a workspace you already fully trust |
| **Plan**         | only plans, never executes a real action                                  |

See [Orchestrator & Subagents](../../concepts/sub-agents) to understand the HITL behind this.

## Orchestrator thinking

The "thinking" block shows the orchestrator's decision before acting: answer directly or delegate to `coder`/`search`, and why. This is real transparency, not just a spinner — you can see the reasoning, not just wait for the result.

## Memory across sessions

A "🧠 N memories loaded" badge appears when the agent uses persistent memories from previous conversations in that response. Manage memories manually in **Settings → Preferences → Memory**.

## RAG citations

Answers based on indexed content bring clickable `[1] [2]` citations — click to see the original excerpt and source.

## Multi-user (Pro)

In Pro mode with multi-user web chat, threads can be shared between members of the same workspace, with RBAC controlling who sees what.

## See also

- [Using the workbench](../using-the-workbench) — the side panel that accompanies chat
- [Using settings](../using-settings) — where the default model, language, and theme live

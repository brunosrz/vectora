---
title: Quick Start
weight: 3
---

This guide gets you from zero to the agent's first response in a few minutes.

## 1. Start Vectora

After [installing](../installation), open the app (or `uv run vectora start --port 8080` + `pnpm --dir frontend dev` in dev mode). The first visit asks you to sign up — the first user to sign up becomes the instance's **root administrator**.

## 2. Configure an LLM provider

Open **Settings → Preferences → General** and pick a provider (Google Gemini, OpenAI, Anthropic, Cohere, or local Ollama). Without an API key configured for any provider, the chat's model selector stays empty.

If you'd rather configure via environment variable instead of the UI, edit `.env` (dev) or `~/.vectora/.env` (native install):

```env
LLM_PROVIDER=google-genai
GOOGLE_API_KEY=your_key_here
COHERE_API_KEY=your_key_here   # required for RAG
```

## 3. Create your first workspace

A workspace is a folder on your filesystem that Vectora can read (and, if you trust it, edit and run commands in). In chat, use the workspace selector at the top to point to a project directory.

The first time you open an untrusted folder, Vectora asks for explicit confirmation ("Trust this folder") before unlocking write access and the terminal — see [First workspace](../first-workspace).

## 4. Send your first message

Try something concrete, not generic:

```text
Explain this project's architecture by reading package.json / pyproject.toml
```

```text
Run the tests and tell me what's failing
```

The orchestrator decides on its own whether to answer directly or delegate to the `coder` subagent (files/git/terminal) or `search` (web search/RAG). Potentially destructive actions (writing a file, running a command, `git push`) pause for your approval — the HITL (human-in-the-loop) mode.

## 5. Index knowledge for RAG (optional, but recommended)

Drag a documentation folder into the chat, or use the **Memory (RAG)** panel in the workbench to index files manually. After that, questions about that content come back with `[1] [2]` citations traceable to the source.

## Next steps

- [Using the chat](../../guides/using-the-chat) — modes, model selector, permission modes
- [Using the workbench](../../guides/using-the-workbench) — the workbench's 9 tabs
- [Concepts: RAG & Context Graph](../../concepts/rag) — how context retrieval works under the hood

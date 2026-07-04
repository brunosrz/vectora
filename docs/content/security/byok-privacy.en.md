---
title: BYOK & Privacy
weight: 4
---

## What "self-hosted" actually guarantees

Your data never passes through a Vectora Company intermediary server. The agent connects **directly** to the APIs you configured (Gemini, OpenAI, Anthropic, Cohere, Tavily) and to the MCP servers you installed. Vectora Company never sees the content of your conversations, your code, or your files.

## What this does not mean

Self-hosted **is not** end-to-end encryption in the classic SaaS sense. The server running Vectora (your server) needs to see the content in the clear to call the LLM and index it for RAG — there's no way to process homomorphically encrypted content with LLMs today. If you access your own Vectora on a VPS from home, data is protected by TLS in transit, strong password hashing, signed JWTs, an AES-256 vault for secrets — but there's **no** encryption such that you yourself (the VPS operator) can't read your own conversations. That's not the threat model.

## BYOK (Bring Your Own Key)

Free and Pro work with your own API keys — LLM, Cohere/VoyageAI (embeddings), Tavily (web search). Vectora never sees or stores those keys in plain text (they live in the [vault](../secrets-vault)); the API call happens directly from your server to the chosen provider.

## LGPD/GDPR

Responsibility for handling data sent to LLM/embedding providers is between **you** (the operator) and **each connected provider** — Vectora isn't part of that data relationship. Vectora Company's Terms of Use describe exactly what travels through each integration.

## Auditing

Pro+ customers receive the compiled binary and complete architecture documentation. Source code auditing under NDA is available for Enterprise customers.

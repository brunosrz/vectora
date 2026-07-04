---
title: Referência de Agents
weight: 4
---

O agente é montado via `create_deep_agent` (LangGraph + [deepagents](https://github.com/langchain-ai/deepagents)) — um supervisor (orchestrator) com dois subagentes.

## orchestrator

Supervisor único, ponto de entrada de toda mensagem. Decide responder direto ou delegar via a tool interna `task`. Tools próprias: `create_artifact`, `save_memory`, `get_memory`, `delete_memory`, além de acesso às tools de RAG pra responder perguntas simples sobre conteúdo já indexado sem precisar delegar.

## coder

Especialista em filesystem, terminal e git. Recebe instruções explícitas do orchestrator (não decide sozinho o que fazer — executa o que foi delegado). Tools: `file_read`, `file_edit`, `file_write`, `grep`, `list_dir`, `terminal`, todas as 14 operações de git, mais acesso a memória e RAG.

## search

Especialista em busca web em tempo real e RAG. Tools: `web_search`, `web_fetch`, `vector_search`, `embedding`, `ingest_docs`, mais memória. Não existe um terceiro subagente dedicado só a RAG — essa responsabilidade é do `search`.

## Middleware

- **HITL** (`HumanInTheLoopMiddleware`) — pausa antes de tool calls destrutivas, com comportamento configurável por [modo de permissão](../../guides/using-the-chat#modos-de-permissão).
- **Contexto** — cada invocação carrega `user_id`, `workspace_id` e `permission_mode` via um `context_schema` tipado.

## Checkpointer

`AsyncSqliteSaver` (modo lite) ou equivalente Postgres (modo complete) — persiste o estado do grafo por thread, permitindo retomar uma conversa exatamente de onde parou.

## Veja também

- [Orchestrator & Subagentes](../../concepts/sub-agents) — visão conceitual
- [Referência de Tools](../tools) — inventário completo

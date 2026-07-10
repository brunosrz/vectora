---
title: Agents Reference
weight: 4
---

El agente está construido vía `create_deep_agent` (LangGraph + [deepagents](https://github.com/langchain-ai/deepagents)) — un supervisor (orquestador) con dos sub-agentes.

## orchestrator

El supervisor único, punto de entrada para cada mensaje. Decide si responde directamente o delega vía la herramienta interna `task`. Sus propias herramientas: `create_artifact`, `save_memory`, `get_memory`, `delete_memory`, además de acceso a herramientas de RAG para responder preguntas simples sobre contenido ya indexado sin delegar.

## coder

Especialista en sistema de archivos, terminal y git. Recibe instrucciones explícitas del orquestador (no decide por su cuenta qué hacer — ejecuta lo que fue delegado). Herramientas: `file_read`, `file_edit`, `file_write`, `grep`, `list_dir`, `terminal`, las 14 operaciones de git, además de acceso a memoria y RAG.

## search

Especialista en búsqueda web en tiempo real y RAG. Herramientas: `web_search`, `web_fetch`, `vector_search`, `embedding`, `ingest_docs`, además de memoria. No hay un tercer sub-agente separado dedicado solo al RAG — esa responsabilidad pertenece a `search`.

## Middleware

- **HITL** (`HumanInTheLoopMiddleware`) — se pausa antes de llamadas a herramientas destructivas, con comportamiento configurable por [modo de permiso](../../guides/using-the-chat#permission-modes).
- **Context** — cada invocación lleva `user_id`, `workspace_id` y `permission_mode` vía un `context_schema` tipado.

## Checkpointer

`AsyncSqliteSaver` (modo lite) o un equivalente de Postgres (modo completo) — persiste el estado del grafo por hilo, permitiéndote reanudar una conversación exactamente donde se quedó.

## Ver también

- [Orchestrator & Subagents](../../concepts/sub-agents) — visión conceptual
- [Referencia de herramientas](../tools) — inventario completo

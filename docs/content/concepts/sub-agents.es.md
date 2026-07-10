---
title: Orchestrator & Subagents
weight: 3
---

El agente de Vectora está construido sobre `create_deep_agent` (LangGraph + [deepagents](https://github.com/langchain-ai/deepagents)) — no un orquestador-por-nodos hecho a mano. Esto da acceso a middleware nativo (HITL configurable), backends de sistema de archivos conectables y un supervisor que delega a sub-agentes especializados vía una herramienta interna `task`.

## Orquestador

El supervisor decide, en cada turno: responder directamente (preguntas simples, conversación general) o delegar a un sub-agente con una instrucción explícita. No hay un salto de enrutamiento innecesario — si la pregunta no necesita un archivo, terminal o búsqueda, el orquestador responde de inmediato.

## Los dos sub-agentes

| Sub-agente | Especialidad                                            | Herramientas principales                                                          |
| ---------- | --------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| **coder**  | Sistema de archivos, terminal, git — generación y revisión de código | `file_read`, `file_edit`, `file_write`, `grep`, `list_dir`, `terminal`, herramientas git |
| **search** | Búsqueda web en tiempo real + RAG                          | `web_search`, `web_fetch`, `vector_search`, `embedding`, `ingest_docs`               |

No hay un tercer sub-agente separado dedicado al RAG — la recuperación de contexto es responsabilidad de `search`, no un sub-agente propio.

## HITL (Human-in-the-Loop)

Antes de cualquier acción destructiva (escribir un archivo, ejecutar un comando de terminal, `git push`), el grafo **se pausa** y pide tu aprobación — vía el `HumanInTheLoopMiddleware` nativo del harness, no un `interrupt()` crudo. El comportamiento cambia según el **modo de permiso** activo:

| Modo              | Comportamiento                                              |
| ------------------ | -------------------------------------------------------------- |
| Siempre preguntar  | toda acción destructiva se pausa                               |
| Aceptar ediciones  | las ediciones de archivos pasan directo; terminal/git aún pausan |
| Autónomo           | nada se pausa (uso avanzado/confiable)                          |
| Plan               | el agente solo planifica, nunca ejecuta                         |

## Por qué esto importa en la práctica

No tienes que confiar ciegamente en el agente: cada llamada a herramienta es rastreable, cada acción riesgosa pasa por ti antes de ocurrir, y la decisión de "responder directo vs. delegar" es visible en la UI (el bloque de "pensamiento" del chat muestra el razonamiento del orquestador).

## Ver también

- [Usando el chat](../../guides/using-the-chat) — modos de permiso en la práctica
- [Referencia de agentes](../../reference/agents) — specs completas de los sub-agentes

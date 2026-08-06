---
title: Introduction
weight: 1
---

## Qué es Vectora

Vectora es un **workspace de IA autoalojado** para equipos de desarrollo. Se ejecuta enteramente en tu servidor — tu VPS, tu máquina local, el servidor de tu empresa — y resuelve dos problemas que la mayoría de los asistentes de IA ignoran: darte a ti y al agente las **mismas superficies de trabajo** (filesystem, terminal, git, navegador — no un chat que narra acciones que nunca ves), y **hacer que el agente realmente conozca tu proyecto**, no solo generar código genérico.

Esto ocurre a través de dos caminos complementarios:

- **RAG híbrido** — indexa código, documentación y decisiones pasadas con búsqueda por palabras clave (BM25) + búsqueda vectorial densa + reranking, de modo que el agente responde según lo indexado, no según lo que "cree" que es cierto.
- **Context Graph nativo** — un grafo de conocimiento del workspace (funciones, clases, conceptos y cómo se relacionan), construido vía parsing AST (tree-sitter) y extracción semántica por LLM. Complementa el RAG con contexto estructural que los embeddings solos no pueden capturar.

## Arquitectura en una imagen

```text
Tú (CLI / Chat web / cliente MCP)
        │
        ▼
   Orquestador (create_deep_agent — LangGraph + deepagents)
        │
   ┌────┴────┐
   ▼         ▼
 coder     search      ← sub-agentes especializados
   │         │
   └────┬────┘
        ▼
  160+ herramientas nativas (archivos, git, terminal, navegador, RAG, web, integraciones)
        │
        ▼
  SQLite + LanceDB (lite, por defecto)  o  Postgres + Qdrant + Redis (completo)
```

El **orquestador** es el supervisor: responde directamente para preguntas simples, o delega a un sub-agente especializado (`coder` para operaciones de archivos/git/terminal, `search` para búsqueda web y RAG) a través de middleware human-in-the-loop (HITL) que pausa antes de acciones destructivas para tu aprobación.

## Tres formas de usarlo

El mismo backend sirve tres superficies distintas, al mismo tiempo:

1. **Chat web** — interfaz React multiusuario, con un workbench (archivos, git, terminal, navegador, RAG, Context Graph, Kanban) compartido entre tú y el agente — ver [Usando el chat](../guides/using-the-chat) y [Usando el workbench](../guides/using-the-workbench).
2. **CLI** — `vectora start`, `vectora config`, `vectora storage` — ver la [referencia de la CLI](../reference/cli).
3. **Cliente MCP** — Vectora se conecta a servidores MCP que instales (un marketplace de conectores, más registro manual) para que el agente use sus herramientas. Vectora no se expone a sí mismo como servidor MCP para otros harnesses — ver [Cliente MCP](../reference/mcp-client).

## Free vs. Pro

Vectora es **software comercial de código cerrado** — lo ejecutas en tu propia infraestructura, pero el código pertenece a Vectora Company (mismo modelo que Cursor, Linear, Notion).

- **Free** — 100% local, sin cuenta, sin ninguna dependencia de Vectora Company. Traes tus propias API keys (LLM, Cohere/Voyage para embeddings, Tavily para búsqueda web). Almacenamiento lite (SQLite + LanceDB).
- **Pro** — opcional, cubre trial/facturación/licenciamiento vía `services.vectora.company` (un pequeño Cloudflare Worker, no una "Vectora Cloud" que aloja tu instancia). Desbloquea chat web multiusuario, almacenamiento completo (Postgres + Qdrant + Redis) y automatizaciones disparadas por webhook.

Consulta los [precios actuales](https://vectora.company/#pricing).

## Siguiente paso

→ [Instalación](../installation)

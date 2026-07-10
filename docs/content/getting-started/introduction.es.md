---
title: Introduction
weight: 1
---

## Qué es Vectora

Vectora es un **agente de IA autoalojado** para equipos de desarrollo. Se ejecuta enteramente en tu servidor — tu VPS, tu máquina local, el servidor de tu empresa — y resuelve el problema que la mayoría de los asistentes de IA ignoran: **hacer que el agente realmente conozca tu proyecto**, no solo generar código genérico.

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
  70+ herramientas nativas (archivos, git, terminal, RAG, web, integraciones)
        │
        ▼
  SQLite + LanceDB (lite, por defecto)  o  Postgres + Qdrant + Redis (completo)
```

El **orquestador** es el supervisor: responde directamente para preguntas simples, o delega a un sub-agente especializado (`coder` para operaciones de archivos/git/terminal, `search` para búsqueda web y RAG) a través de middleware human-in-the-loop (HITL) que pausa antes de acciones destructivas para tu aprobación.

## Cuatro formas de usarlo

El mismo backend sirve cuatro superficies distintas, al mismo tiempo:

1. **Chat web** — interfaz React multiusuario, con un workbench (archivos, git, terminal, RAG, Context Graph) — ver [Usando el chat](../guides/using-the-chat) y [Usando el workbench](../guides/using-the-workbench).
2. **CLI** — `vectora start`, `vectora config`, `vectora storage` — ver la [referencia de la CLI](../reference/cli).
3. **Servidor MCP** — montado en `/mcp` en el mismo proceso, siempre activo. Conecta Claude Code, Claude Desktop o cualquier cliente MCP — ver [Servidor MCP](../reference/mcp-server).
4. **API REST** — endpoints `/v1/classify`, `/v1/extract` y `/v1/jobs` para integrar el agente en otros sistemas — ver [Referencia de la API](../api-reference/overview).

## Free vs. Pro

Vectora es **software comercial de código cerrado** — lo ejecutas en tu propia infraestructura, pero el código pertenece a Vectora Company (mismo modelo que Cursor, Linear, Notion).

- **Free** — 100% local, sin cuenta, sin ninguna dependencia de Vectora Company. Traes tus propias API keys (LLM, Cohere/Voyage para embeddings, Tavily para búsqueda web). Almacenamiento lite (SQLite + LanceDB).
- **Pro** — opcional, cubre trial/facturación/licenciamiento vía `services.vectora.company` (un pequeño Cloudflare Worker, no una "Vectora Cloud" que aloja tu instancia). Desbloquea chat web multiusuario, almacenamiento completo (Postgres + Qdrant + Redis), webhooks y la API REST con un límite de tasa más alto.

Consulta los [precios actuales](https://vectora.company/#pricing).

## Siguiente paso

→ [Instalación](../installation)

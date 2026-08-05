---
title: Documentation
type: docs
cascade:
  type: docs
sidebar:
  open: true
---

Vectora es un **agente de IA autoalojado** — se ejecuta enteramente en tu propio servidor, se integra como sub-agente en cualquier orquestador compatible con MCP (Claude Code, Claude Desktop, extensiones de VS Code) y viene con un chat web completo multiusuario.

En su núcleo, Vectora cierra la **brecha de conocimiento** entre un LLM y tu código, documentación y stack actuales: un pipeline **RAG** híbrido (BM25 + vectores densos + reranker) para recuperación por similitud, y un **Context Graph** nativo (workspace analizado vía tree-sitter + extracción por LLM) para contexto estructural.

## Por dónde empezar

| Quiero...                                  | Ir a                                             |
| ------------------------------------------- | ------------------------------------------------- |
| Instalar Vectora                            | [Instalación](./getting-started/installation)      |
| Ejecutarlo en 5 minutos                     | [Inicio rápido](./getting-started/quick-start)   |
| Entender el pipeline RAG                    | [RAG y Context Graph](./concepts/rag)             |
| Conectar un cliente MCP (Claude Code...)    | [Servidor MCP](./reference/mcp-server)            |
| Ver todos los comandos de la CLI            | [Referencia de la CLI](./reference/cli)           |
| Desplegar en un servidor                    | [Requisitos](./deployment/requirements)           |
| Entender auth, secretos y BYOK              | [Seguridad](./security/authentication)            |
| Usar la API REST                            | [Referencia de la API](./api-reference)  |

## Qué es Vectora (y qué no es)

Vectora es **software comercial de código cerrado** — no es open source. Lo ejecutas en tu propia infraestructura (tu servidor, tu VPS, tu escritorio), pero el código fuente pertenece a Vectora Company. Es el mismo modelo que Cursor, Linear o Notion: la infra es tuya, el código es del proveedor.

- **Free** se ejecuta 100% localmente, sin necesidad de cuenta. Traes tus propias API keys.
- **Pro** es opcional y cubre trial/facturación/licenciamiento vía `services.vectora.company`, un pequeño Cloudflare Worker — no es una "Vectora Cloud" que aloja o ejecuta tu instancia por ti. Actualizar cambia qué funciones están disponibles (stack de almacenamiento de alto rendimiento, chat web multiusuario, webhooks, API REST), nunca dónde se ejecuta el agente.

Consulta la [página de precios](https://vectora.company/#pricing) para los planes actuales.

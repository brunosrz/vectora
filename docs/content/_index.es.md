---
title: Documentation
type: docs
cascade:
  type: docs
sidebar:
  open: true
---

Vectora es un **workspace de IA autoalojado** — se ejecuta enteramente en tu propio servidor, y tú y el agente trabajan lado a lado en el mismo filesystem, terminal, git y navegador. Viene con un chat web completo multiusuario y un cliente nativo de conectores para los servidores MCP que decidas instalar.

En su núcleo, Vectora cierra la **brecha de conocimiento** entre un LLM y tu código, documentación y stack actuales: un pipeline **RAG** híbrido (BM25 + vectores densos + reranker) para recuperación por similitud, y un **Context Graph** nativo (workspace analizado vía tree-sitter + extracción por LLM) para contexto estructural.

## Por dónde empezar

| Quiero...                                  | Ir a                                             |
| ------------------------------------------- | ------------------------------------------------- |
| Instalar Vectora                            | [Instalación](./getting-started/installation)      |
| Ejecutarlo en 5 minutos                     | [Inicio rápido](./getting-started/quick-start)   |
| Entender el pipeline RAG                    | [RAG y Context Graph](./concepts/rag)             |
| Conectar un servidor MCP (como cliente)     | [Cliente MCP](./reference/mcp-client)             |
| Ver todos los comandos de la CLI            | [Referencia de la CLI](./reference/cli)           |
| Desplegar en un servidor                    | [Requisitos](./deployment/requirements)           |
| Entender auth, secretos y BYOK              | [Seguridad](./security/authentication)            |

## Qué es Vectora (y qué no es)

Vectora es **software comercial de código cerrado** — no es open source. Lo ejecutas en tu propia infraestructura (tu servidor, tu VPS, tu escritorio), pero el código fuente pertenece a Vectora Company. Es el mismo modelo que Cursor, Linear o Notion: la infra es tuya, el código es del proveedor.

- **Free** se ejecuta 100% localmente, sin necesidad de cuenta. Traes tus propias API keys.
- **Pro** es opcional y cubre trial/facturación/licenciamiento vía `services.vectora.company`, un pequeño Cloudflare Worker — no es una "Vectora Cloud" que aloja o ejecuta tu instancia por ti. Actualizar cambia qué funciones están disponibles (stack de almacenamiento de alto rendimiento, chat web multiusuario, automatizaciones disparadas por webhook), nunca dónde se ejecuta el agente.

Consulta la [página de precios](https://vectora.company/#pricing) para los planes actuales.

---
title: Troubleshooting
weight: 6
---

## El selector de modelos está vacío

Ningún proveedor de LLM tiene una API key configurada. Ve a **Configuración → Preferencias → General** (o edita `.env`/`~/.vectora/.env`) y agrega al menos una: `GOOGLE_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `COHERE_API_KEY`, o configura un endpoint local de Ollama.

## El RAG no devuelve resultados / errores de embedding

El RAG depende de `COHERE_API_KEY` (o una key de VoyageAI configurada como alternativa) para generar embeddings y hacer reranking. Sin ella, la indexación falla silenciosamente o la búsqueda vectorial no devuelve nada. Verifica la key en **Configuración → Entorno → Envs**.

## El agente no puede escribir archivos / ejecutar comandos

El workspace probablemente sigue **sin confianza**. Ver [Primer workspace](../first-workspace) — haz clic en "Confiar en esta carpeta" para desbloquear la escritura y la terminal.

## Un cliente MCP externo (Claude Code, Claude Desktop) no se conecta

Confirma que Vectora esté ejecutándose y que la URL usada sea `http://<tu-host>:<puerto>/mcp` (no `/mcp/sse` — el servidor se monta directamente en `/mcp` vía SSE en el mismo proceso). En producción, usa la URL HTTPS pública de tu servidor. Ver [Servidor MCP](../../reference/mcp-server).

## `vectora storage complete` no se conecta a Postgres/Qdrant/Redis

El modo completo requiere que los tres servicios estén accesibles en los DSN configurados (`POSTGRES_DSN`, `QDRANT_URL`, `REDIS_URL`). Si no tienes tu propia infraestructura, ejecuta `scons docker` (desde la raíz del monorepo, si ejecutas desde el código fuente) o usa `vectora storage wizard` para configurar un proveedor gestionado (Supabase, Neon, Qdrant Cloud). Ver [Almacenamiento: lite vs. completo](../../concepts/storage).

## Las funciones Pro (chat multiusuario, almacenamiento completo) no se desbloquean pese a tener una suscripción activa

Confirma que tu `VECTORA_TOKEN` del [dashboard](https://vectora.company/dashboard) esté configurado y sea válido — el estado de la licencia se cachea localmente con un TTL corto; fuerza una revalidación reiniciando la app o revisando **Configuración → Administración → Sistema**.

## Error `command not found: vectora` (instalación desde código fuente)

Ejecuta con `uv run vectora ...` en lugar de `vectora ...` directamente — `uv` gestiona el entorno virtual y el entrypoint sin una instalación global.

## Dónde reportar un error

[GitHub Issues](https://github.com/vectora-company/vectora/issues) (público) o el formulario en [vectora.company/issues](https://vectora.company/issues).

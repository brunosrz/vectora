---
title: Configuration (Reference)
weight: 2
---

## `~/.vectora/config.toml`

Configuración de runtime, generada/editada por `vectora config` o la UI de Configuración. Ejemplo mínimo:

```toml
[global]
mode = "desktop"   # o "cli", "headless", "mcp", "web"

[runtime]
auto_update = true

[server]
host = "0.0.0.0"
port = 8080
```

## Principales variables de entorno

| Variable                                                    | ¿Requerida?          | Descripción                                                    |
| -------------------------------------------------------------- | ---------------------- | ------------------------------------------------------------------ |
| `LLM_PROVIDER`                                                  | Sí                     | `google-genai`, `openai`, `anthropic`, `cohere`, u `ollama`        |
| `GOOGLE_API_KEY` / `OPENAI_API_KEY` / `ANTHROPIC_API_KEY`      | Depende del proveedor  | la key del proveedor de LLM elegido                                 |
| `COHERE_API_KEY`                                                | Sí (para RAG)          | embeddings + reranking                                              |
| `TAVILY_API_KEY`                                                | Opcional               | búsqueda web                                                        |
| `STORAGE_MODE`                                                  | No (por defecto `lite`) | `lite` o `complete` — ver [Almacenamiento](../../concepts/storage)  |
| `POSTGRES_DSN`                                                  | Solo en `complete`     | ej. `postgresql+asyncpg://user:pass@host:5432/vectora`             |
| `QDRANT_URL` / `QDRANT_API_KEY`                                 | Solo en `complete`     | endpoint de Qdrant                                                  |
| `REDIS_URL`                                                     | Solo en `complete`     | endpoint de Redis                                                   |
| `LANGSMITH_TRACING`                                             | Opcional               | `true`/`false` — observabilidad externa                             |
| `LANGSMITH_API_KEY`                                             | Opcional               | solo si el tracing está habilitado                                  |

## Jerarquía

```text
defaults.env (integrado)  →  .env (proyecto)  →  ~/.vectora/.env (usuario)  →  sobreescrituras por usuario (base de datos)
```

Ver [Configuration](../../getting-started/configuration) para la guía de uso completa.

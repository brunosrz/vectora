---
title: CLI Reference
weight: 1
---

```text
vectora [comando] [opciones]
```

## Comandos

| Comando             | Qué hace                                                              |
| -------------------- | ------------------------------------------------------------------------ |
| _(sin args)_         | imprime ayuda                                                            |
| `start`              | inicia el backend completo + MCP (`/mcp`) + la SPA (fullstack)          |
| `start --headless`   | inicia sin abrir ventana (backend + MCP + bandeja)                       |
| `config`             | muestra/edita configuración; subcomandos: `keys`, `docker`, `qdrant`, `redis` |
| `storage`            | migraciones, diagnósticos, backup/restauración, wizard de BaaS          |
| `sessions`           | lista todas las sesiones guardadas                                       |

## Opciones de `start`

| Opción                                    | Por defecto | Descripción                                        |
| -------------------------------------------- | ------------- | ----------------------------------------------------- |
| `--headless`                                 | —             | no abre ventana (mantiene backend + MCP + bandeja)   |
| `--host <host>`                              | `0.0.0.0`     | host de escucha                                       |
| `--port <n>`                                 | `8080`        | puerto                                                 |
| `--ssl-certfile` / `--ssl-keyfile <pem>`     | —             | servir vía `https://`                                  |

## `vectora config`

```bash
vectora config keys         # wizard interactivo para API keys + proveedor de LLM
vectora config docker up    # levanta Postgres + Redis + Qdrant locales (Docker)
vectora config qdrant       # configuración específica de Qdrant
vectora config redis        # configuración específica de Redis
```

## `vectora storage`

```bash
vectora storage wizard                       # wizard de infra gestionada (Supabase/Neon/Qdrant Cloud/autoalojado)
vectora storage migrate status               # migraciones aplicadas/pendientes
vectora storage migrate upgrade              # aplica migraciones pendientes
vectora storage migrate to-postgres          # SQLite → Postgres
vectora storage migrate to-qdrant <collection> # LanceDB → Qdrant
vectora storage migrate to-pgvector          # LanceDB → pgvector
vectora storage migrate memory-to-langgraph  # memorias antiguas → BaseStore
```

Ver [Almacenamiento: lite vs. completo](../../concepts/storage) para el contexto completo.

## `vectora sessions`

```bash
vectora sessions
```

Lista todas las sesiones (hilos) guardadas localmente.

## Uso típico en un VPS vía SSH

El frontend cubre la configuración del día a día, pero en un servidor headless la CLI expone lo esencial:

```bash
uv run vectora config keys         # configurar API keys
uv run vectora config docker up    # levantar infraestructura opcional
uv run vectora start --headless    # backend + MCP, sin ventana
```

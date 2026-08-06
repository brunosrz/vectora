---
title: Referência de CLI
weight: 1
---

```text
vectora [comando] [opções]
```

## Comandos

| Comando            | O que faz                                                               |
| ------------------ | ----------------------------------------------------------------------- |
| _(sem args)_       | imprime a ajuda                                                         |
| `start`            | sobe o backend completo + a SPA (fullstack)                            |
| `start --headless` | sobe sem abrir janela (backend + bandeja)                               |
| `config`           | mostra/edita settings; subcomandos: `keys`, `docker`, `qdrant`, `redis` |
| `storage`          | migrations, diagnóstico, backup/restore, wizard de BaaS                 |
| `sessions`         | lista todas as sessões salvas                                           |

## Opções de `start`

| Opção                                    | Padrão    | Descrição                                        |
| ---------------------------------------- | --------- | ------------------------------------------------ |
| `--headless`                             | —         | não abre janela (mantém backend + MCP + bandeja) |
| `--host <host>`                          | `0.0.0.0` | host de escuta                                   |
| `--port <n>`                             | `8080`    | porta                                            |
| `--ssl-certfile` / `--ssl-keyfile <pem>` | —         | serve em `https://`                              |

## `vectora config`

```bash
vectora config keys         # wizard interativo de chaves de API + provider de LLM
vectora config docker up    # sobe Postgres + Redis + Qdrant local (Docker)
vectora config qdrant       # config específica de Qdrant
vectora config redis        # config específica de Redis
```

## `vectora storage`

```bash
vectora storage wizard                       # wizard de infra gerenciada (Supabase/Neon/Qdrant Cloud/self-hosted)
vectora storage migrate status               # migrations aplicadas/pendentes
vectora storage migrate upgrade              # aplica migrations pendentes
vectora storage migrate to-postgres          # SQLite → Postgres
vectora storage migrate to-qdrant <coleção>  # LanceDB → Qdrant
vectora storage migrate to-pgvector          # LanceDB → pgvector
vectora storage migrate memory-to-langgraph  # memórias antigas → BaseStore
```

Veja [Storage: lite vs. complete](../../concepts/storage) pro contexto completo.

## `vectora sessions`

```bash
vectora sessions
```

Lista todas as sessões (threads) salvas localmente.

## Uso típico numa VPS via SSH

O frontend cobre toda a configuração do dia a dia, mas em um servidor sem interface gráfica a CLI expõe o essencial:

```bash
uv run vectora config keys         # configura chaves de API
uv run vectora config docker up    # sobe infraestrutura opcional
uv run vectora start --headless    # backend + MCP, sem janela
```

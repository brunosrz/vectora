---
title: Visão Geral
weight: 1
---

## Base URL

```text
http://localhost:8080/v1        # dev / local
https://vectora.seudominio.com/v1   # produção
```

## Autenticação

Os endpoints `/v1/*` são **públicos** (sem token obrigatório) — o rate limit é o que diferencia por tier. Usuário anônimo é tratado como tier "Free" pra fins de rate limit.

## Rate limit por tier

| Tier | Requisições/minuto |
| ---- | ------------------ |
| Free | 10/min             |
| Pro  | 100/min            |

## Documentação OpenAPI automática

FastAPI gera a spec automaticamente:

```text
GET /docs           # Swagger UI interativo
GET /openapi.json   # spec OpenAPI 3.x crua
```

## Endpoints

| Método | Path                           | Descrição                                                            |
| ------ | ------------------------------ | -------------------------------------------------------------------- |
| `POST` | `/v1/classify`                 | Classifica um texto em uma ou mais labels                            |
| `POST` | `/v1/extract`                  | Extrai dados estruturados de um texto livre, conforme um JSON Schema |
| `POST` | `/v1/jobs`                     | Submete um job assíncrono                                            |
| `GET`  | `/v1/jobs/{request_id}/events` | Acompanha um job via Server-Sent Events                              |

Veja o roadmap completo — SDKs Python/TypeScript, webhooks, e endpoints adicionais de chat/documentos — em [Roadmap da API](./roadmap).

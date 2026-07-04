---
title: "POST /v1/jobs + SSE"
weight: 4
---

Submete um job assíncrono e acompanha o progresso via Server-Sent Events — útil pra operações que não cabem no ciclo request/response síncrono de `/classify` e `/extract`.

## Submeter um job

```http
POST /v1/jobs
```

```json
{
  "kind": "echo",
  "payload": { "message": "hello" }
}
```

| Campo     | Tipo   | Obrigatório       | Descrição                        |
| --------- | ------ | ----------------- | -------------------------------- |
| `kind`    | string | Sim               | Tipo do job (ex: `"echo"`)       |
| `payload` | object | Não (padrão `{}`) | Dados específicos daquele `kind` |

### Response

```json
{
  "request_id": "req_01jxxxxxxxxxx",
  "kind": "echo"
}
```

## Acompanhar via SSE

```http
GET /v1/jobs/{request_id}/events
```

Retorna um stream de Server-Sent Events com o status do job até a conclusão:

```text
data: {"status": "running"}

data: {"status": "done", "result": {...}}
```

Estados possíveis: `running`, `done`, `error`. Este endpoint não tem rate limit próprio — é um long-poll SSE.

## Rate limit (submissão)

10/min (Free) ou 100/min (Pro) pra `POST /v1/jobs` — veja [Visão Geral](../overview).

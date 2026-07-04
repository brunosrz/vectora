---
title: POST /v1/extract
weight: 3
---

Extrai dados estruturados de um texto livre, conforme um **JSON Schema** (Draft 7) fornecido — o schema é convertido pra um modelo Pydantic dinamicamente, e o deep-agent usa `response_format` pra garantir que a saída bate com ele.

## Request

```json
{
  "text": "João Silva, joao@example.com, quer agendar uma call pra sexta às 14h",
  "schema": {
    "type": "object",
    "properties": {
      "nome": { "type": "string" },
      "email": { "type": "string" },
      "dia_semana": { "type": "string" },
      "horario": { "type": "string" }
    },
    "required": ["nome", "email"]
  }
}
```

| Campo    | Tipo   | Obrigatório | Descrição                                          |
| -------- | ------ | ----------- | -------------------------------------------------- |
| `text`   | string | Sim         | Texto de onde extrair os dados                     |
| `schema` | object | Sim         | JSON Schema (Draft 7) descrevendo a forma esperada |

## Response

```json
{
  "data": {
    "nome": "João Silva",
    "email": "joao@example.com",
    "dia_semana": "sexta",
    "horario": "14h"
  },
  "strategy": "auto"
}
```

| Campo      | Tipo   | Descrição                                                                             |
| ---------- | ------ | ------------------------------------------------------------------------------------- |
| `data`     | object | Dados extraídos, validados conforme o schema                                          |
| `strategy` | string | `provider` (structured output nativo do modelo) ou `tool` (fallback via tool calling) |

## Rate limit

10/min (Free) ou 100/min (Pro) — veja [Visão Geral](../overview).

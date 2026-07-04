---
title: POST /v1/extract
weight: 3
---

Extracts structured data from free text, according to a provided **JSON Schema** (Draft 7) — the schema is dynamically converted into a Pydantic model, and the deep-agent uses `response_format` to make sure the output matches it.

## Request

```json
{
  "text": "John Smith, john@example.com, wants to schedule a call for Friday at 2pm",
  "schema": {
    "type": "object",
    "properties": {
      "name": { "type": "string" },
      "email": { "type": "string" },
      "weekday": { "type": "string" },
      "time": { "type": "string" }
    },
    "required": ["name", "email"]
  }
}
```

| Field    | Type   | Required | Description                                         |
| -------- | ------ | -------- | --------------------------------------------------- |
| `text`   | string | Yes      | Text to extract data from                           |
| `schema` | object | Yes      | JSON Schema (Draft 7) describing the expected shape |

## Response

```json
{
  "data": {
    "name": "John Smith",
    "email": "john@example.com",
    "weekday": "Friday",
    "time": "2pm"
  },
  "strategy": "auto"
}
```

| Field      | Type   | Description                                                                   |
| ---------- | ------ | ----------------------------------------------------------------------------- |
| `data`     | object | Extracted data, validated against the schema                                  |
| `strategy` | string | `provider` (model-native structured output) or `tool` (tool-calling fallback) |

## Rate limit

10/min (Free) or 100/min (Pro) — see [Overview](../overview).

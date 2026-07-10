---
title: POST /v1/extract
weight: 3
---

Extrae datos estructurados de texto libre, según un **JSON Schema** provisto (Draft 7) — el schema se convierte dinámicamente en un modelo Pydantic, y el deep-agent usa `response_format` para asegurar que la salida coincida con él.

## Solicitud

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

| Campo    | Tipo   | Requerido | Descripción                                             |
| -------- | ------ | ---------- | ----------------------------------------------------------- |
| `text`   | string | Sí         | Texto del que extraer datos                                 |
| `schema` | object | Sí         | JSON Schema (Draft 7) describiendo la forma esperada         |

## Respuesta

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

| Campo      | Tipo   | Descripción                                                                     |
| ---------- | ------ | ------------------------------------------------------------------------------- |
| `data`     | object | Datos extraídos, validados contra el schema                                     |
| `strategy` | string | `provider` (salida estructurada nativa del modelo) o `tool` (fallback por herramienta) |

## Límite de tasa

10/min (Free) o 100/min (Pro) — ver [Overview](../overview).

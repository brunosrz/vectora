---
title: POST /v1/classify
weight: 2
---

Clasifica un texto en una o más etiquetas provistas, usando el `response_format` estructurado del deep-agent (autodetecta el `ProviderStrategy` nativo del modelo o recae en `ToolStrategy`).

## Solicitud

```json
{
  "text": "The app crashes every time I try to export a PDF",
  "labels": ["bug", "feature-request", "question", "praise"],
  "multi_label": false,
  "description": "Categorizes user feedback"
}
```

| Campo         | Tipo     | Requerido              | Descripción                                              |
| ------------- | -------- | ----------------------- | ------------------------------------------------------------ |
| `text`        | string   | Sí                       | Texto a clasificar                                            |
| `labels`      | string[] | Sí                       | 2 o más etiquetas posibles                                     |
| `multi_label` | bool     | No (por defecto `false`) | Si `true`, permite más de una etiqueta en la respuesta         |
| `description` | string   | No                       | Contexto extra para guiar la clasificación                    |

## Respuesta

```json
{
  "label": "bug",
  "confidence": 0.94,
  "labels": [],
  "reasoning": "Mentions a consistent crash tied to a specific action (exporting a PDF)",
  "strategy": "auto"
}
```

| Campo        | Tipo            | Descripción                                                        |
| ------------ | ---------------- | ------------------------------------------------------------------- |
| `label`      | string           | Etiqueta más probable                                                |
| `confidence` | float            | 0.0–1.0                                                              |
| `labels`     | string[]         | Todas las etiquetas aplicables (solo se llena si `multi_label: true`) |
| `reasoning`  | string \| null   | Justificación de la clasificación                                    |
| `strategy`   | string           | Estrategia usada internamente (`provider` o `tool`)                  |

## Límite de tasa

10/min (Free) o 100/min (Pro) — ver [Overview](../overview).

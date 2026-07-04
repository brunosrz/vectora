---
title: POST /v1/classify
weight: 2
---

Classifies a text into one or more provided labels, using the deep-agent's structured `response_format` (auto-detects the model's native `ProviderStrategy` or falls back to `ToolStrategy`).

## Request

```json
{
  "text": "The app crashes every time I try to export a PDF",
  "labels": ["bug", "feature-request", "question", "praise"],
  "multi_label": false,
  "description": "Categorizes user feedback"
}
```

| Field         | Type     | Required             | Description                                           |
| ------------- | -------- | -------------------- | ----------------------------------------------------- |
| `text`        | string   | Yes                  | Text to classify                                      |
| `labels`      | string[] | Yes                  | 2 or more possible labels                             |
| `multi_label` | bool     | No (default `false`) | If `true`, allows more than one label in the response |
| `description` | string   | No                   | Extra context to guide classification                 |

## Response

```json
{
  "label": "bug",
  "confidence": 0.94,
  "labels": [],
  "reasoning": "Mentions a consistent crash tied to a specific action (exporting a PDF)",
  "strategy": "auto"
}
```

| Field        | Type           | Description                                                   |
| ------------ | -------------- | ------------------------------------------------------------- |
| `label`      | string         | Most likely label                                             |
| `confidence` | float          | 0.0–1.0                                                       |
| `labels`     | string[]       | All applicable labels (only populated if `multi_label: true`) |
| `reasoning`  | string \| null | Justification for the classification                          |
| `strategy`   | string         | Strategy used internally (`provider` or `tool`)               |

## Rate limit

10/min (Free) or 100/min (Pro) — see [Overview](../overview).

---
title: Overview
weight: 1
---

## Base URL

```text
http://localhost:8080/v1        # dev / local
https://vectora.yourdomain.com/v1   # production
```

## Authentication

The `/v1/*` endpoints are **public** (no token required) — rate limit is what differentiates tiers. Anonymous users are treated as the "Free" tier for rate-limiting purposes.

## Rate limit by tier

| Tier | Requests/minute |
| ---- | --------------- |
| Free | 10/min          |
| Pro  | 100/min         |

## Automatic OpenAPI documentation

FastAPI generates the spec automatically:

```text
GET /docs           # interactive Swagger UI
GET /openapi.json   # raw OpenAPI 3.x spec
```

## Endpoints

| Method | Path                           | Description                                                |
| ------ | ------------------------------ | ---------------------------------------------------------- |
| `POST` | `/v1/classify`                 | Classifies a text into one or more labels                  |
| `POST` | `/v1/extract`                  | Extracts structured data from free text, per a JSON Schema |
| `POST` | `/v1/jobs`                     | Submits an async job                                       |
| `GET`  | `/v1/jobs/{request_id}/events` | Tracks a job via Server-Sent Events                        |

See the full roadmap — Python/TypeScript SDKs, webhooks, and additional chat/documents endpoints — at [API roadmap](./roadmap).

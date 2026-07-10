---
title: Overview
weight: 1
---

## URL base

```text
http://localhost:8080/v1        # dev / local
https://vectora.yourdomain.com/v1   # producción
```

## Autenticación

Los endpoints `/v1/*` son **públicos** (no requieren token) — el límite de tasa es lo que diferencia los niveles. Los usuarios anónimos se tratan como nivel "Free" para efectos de rate-limiting.

## Límite de tasa por nivel

| Nivel | Solicitudes/minuto |
| ----- | -------------------- |
| Free  | 10/min                |
| Pro   | 100/min                |

## Documentación automática de OpenAPI

FastAPI genera el spec automáticamente:

```text
GET /docs           # Swagger UI interactivo
GET /openapi.json   # spec OpenAPI 3.x crudo
```

## Endpoints

| Método | Ruta                            | Descripción                                                  |
| ------- | -------------------------------- | ---------------------------------------------------------------- |
| `POST`  | `/v1/classify`                   | Clasifica un texto en una o más etiquetas                        |
| `POST`  | `/v1/extract`                    | Extrae datos estructurados de texto libre, según un JSON Schema  |
| `POST`  | `/v1/jobs`                       | Envía un job asíncrono                                           |
| `GET`   | `/v1/jobs/{request_id}/events`   | Sigue un job vía Server-Sent Events                               |

Consulta el roadmap completo — SDKs de Python/TypeScript, webhooks y endpoints adicionales de chat/documentos — en [API roadmap](./roadmap).

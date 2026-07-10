---
title: "POST /v1/jobs + SSE"
weight: 4
---

Envía un job asíncrono y sigue el progreso vía Server-Sent Events — útil para operaciones que no encajan en el ciclo síncrono de solicitud/respuesta de `/classify` y `/extract`.

## Enviar un job

```http
POST /v1/jobs
```

```json
{
  "kind": "echo",
  "payload": { "message": "hello" }
}
```

| Campo     | Tipo   | Requerido           | Descripción                        |
| --------- | ------ | --------------------- | -------------------------------------- |
| `kind`    | string | Sí                     | El tipo de job (ej.: `"echo"`)         |
| `payload` | object | No (por defecto `{}`) | Datos específicos de ese `kind`        |

### Respuesta

```json
{
  "request_id": "req_01jxxxxxxxxxx",
  "kind": "echo"
}
```

## Seguimiento vía SSE

```http
GET /v1/jobs/{request_id}/events
```

Devuelve un stream de Server-Sent Events con el estado del job hasta su finalización:

```text
data: {"status": "running"}

data: {"status": "done", "result": {...}}
```

Estados posibles: `running`, `done`, `error`. Este endpoint no tiene límite de tasa propio — es un SSE de long-poll.

## Límite de tasa (envío)

10/min (Free) o 100/min (Pro) para `POST /v1/jobs` — ver [Overview](../overview).

---
title: "POST /v1/jobs + SSE"
weight: 4
---

Submits an async job and tracks progress via Server-Sent Events — useful for operations that don't fit into the synchronous request/response cycle of `/classify` and `/extract`.

## Submit a job

```http
POST /v1/jobs
```

```json
{
  "kind": "echo",
  "payload": { "message": "hello" }
}
```

| Field     | Type   | Required          | Description                   |
| --------- | ------ | ----------------- | ----------------------------- |
| `kind`    | string | Yes               | The job type (e.g., `"echo"`) |
| `payload` | object | No (default `{}`) | Data specific to that `kind`  |

### Response

```json
{
  "request_id": "req_01jxxxxxxxxxx",
  "kind": "echo"
}
```

## Tracking via SSE

```http
GET /v1/jobs/{request_id}/events
```

Returns a stream of Server-Sent Events with the job's status until completion:

```text
data: {"status": "running"}

data: {"status": "done", "result": {...}}
```

Possible states: `running`, `done`, `error`. This endpoint has no rate limit of its own — it's a long-poll SSE.

## Rate limit (submission)

10/min (Free) or 100/min (Pro) for `POST /v1/jobs` — see [Overview](../overview).

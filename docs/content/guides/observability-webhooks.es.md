---
title: Webhooks de Observabilidad
weight: 7
---

La infraestructura de webhooks de Vectora (`backend/api/handlers/webhooks.py`) trae soporte nativo para varios proveedores (GitHub, GitLab, Slack, Linear, email). Para herramientas de alertas y observabilidad — Sentry, Grafana, PagerDuty y el resto de ese espacio — no hay un parser específico por proveedor. En su lugar hay un endpoint genérico con un contrato de payload fijo y documentado: apunta el webhook de salida de tu herramienta a él, y ajusta el payload para que coincida con la forma de abajo.

Esta es una decisión deliberada. Un parser dedicado de Sentry/Grafana/PagerDuty necesitaría seguir el formato de payload de cada proveedor a medida que evoluciona; un contrato fijo nunca queda obsoleto, a costa de que hagas el mapeo de campos una vez en la configuración de webhook de tu herramienta de alertas.

## Endpoint

```
POST /webhook/observability
X-Webhook-Secret: <tu secreto>
Content-Type: application/json

{
  "title": "Error 500 en /checkout",
  "description": "NullPointerException en la pasarela de pago",
  "severity": "critical",
  "url": "https://sentry.io/issues/1",
  "external_id": "sentry-1"
}
```

| Campo         | Requerido | Notas                                                                 |
|---------------|-----------|------------------------------------------------------------------------|
| `title`       | sí        | Se convierte en el nombre de la tarjeta del Kanban.                   |
| `external_id` | sí        | Clave de idempotencia — un id estable de tu herramienta de alertas (id de la alerta/incidente). Reenviar el mismo `external_id` actualiza la tarjeta existente en lugar de crear un duplicado. |
| `description` | no        | Se convierte en el cuerpo de la instrucción de la tarjeta (truncado a 2000 caracteres). |
| `severity`    | no        | `critical` / `high` / `medium` / `low`. Ver el mapeo abajo.            |
| `url`         | no        | Enlace de vuelta a la alerta en tu herramienta, guardado en la tarjeta. |

La autenticación es un secreto estático, no una firma HMAC: configura `OBSERVABILITY_WEBHOOK_SECRET` en el backend y envíalo de vuelta en el header `X-Webhook-Secret` en cada petición. Un secreto ausente o incorrecto devuelve `401` antes incluso de que el payload se parsee. Un cuerpo malformado, o que falte `title`/`external_id`, devuelve `400`.

## Severidad → estado del Kanban

El tablero Kanban no tiene un campo de prioridad nativo, así que la severidad se mapea al estado inicial de la tarjeta:

- `critical` / `high` → **triage** (necesita atención inmediata)
- `medium` / `low` (o ausente/no reconocido) → **todo**

Reenviar el evento reevalúa la severidad y mueve la tarjeta en consecuencia — una alerta que empezó como `critical` y luego reporta `low` en un payload posterior sale de triage.

## Activando la sincronización

Igual que la sincronización de Issues de GitHub → Kanban, esto viene desactivado por defecto. Se activa cuando existe al menos una tarea en segundo plano `webhook` habilitada cuyo `trigger_config` es `{"provider": "observability"}` — la sesión y el workspace de esa tarea se convierten en la base de cada tarjeta que crea la sincronización. Sin esa tarea, el endpoint sigue aceptando y persistiendo eventos (así que no se pierde nada mientras configuras todo), pero no se crea ninguna tarjeta.

Esto se ejecuta completamente sin el LLM: es un insert-or-update determinista contra la misma tabla `vectora_background_tasks` que usa el resto del modelo de Kanban (`backend/scheduling/background_tasks.py::sync_observability_alert_to_kanban`), el mismo patrón que ya estableció la sincronización de Issues de GitHub (`sync_github_issue_to_kanban`).

## Ejemplos de configuración por proveedor

Estos son mapeos honestos de mejor esfuerzo — ninguna de estas herramientas habla el contrato de Vectora de forma nativa, así que estás traduciendo su payload de webhook saliente a la forma de arriba, típicamente vía la función de "payload personalizado" o plantillas de cada herramienta cuando esté disponible, o un relay ligero en caso contrario.

### Sentry — Alert Rules → Webhook Action

1. **Settings → Alerts → Rules** → edita o crea una regla.
2. Añade una acción del tipo **"Send a notification via an integration"** → **Webhook**, o usa **Internal Integrations** (**Settings → Developer Settings → Custom Integrations**) para obtener una URL de webhook dedicada con más control sobre el payload.
3. Apunta la URL del webhook a `https://<tu-backend>/webhook/observability`.
4. Configura el header `X-Webhook-Secret` con el valor de tu `OBSERVABILITY_WEBHOOK_SECRET` (los headers personalizados están disponibles en Internal Integrations; los webhooks simples de Alert Rule pueden necesitar un pequeño relay si tu plan de Sentry no soporta headers personalizados).
5. Mapea los campos del payload de Sentry a los de Vectora: `event.title` → `title`, `event.culprit`/`event.message` → `description`, `event.level` (`fatal`/`error` → `critical`/`high`, `warning` → `medium`, `info`/`debug` → `low`) → `severity`, `url` → `url`, `event.event_id` o el id del issue → `external_id`.

### Grafana Alerting — Contact Point (Webhook)

1. **Alerting → Contact points → Add contact point**.
2. Tipo de integración: **Webhook**.
3. URL: `https://<tu-backend>/webhook/observability`.
4. En **Optional Webhook settings**, añade un header HTTP personalizado `X-Webhook-Secret` con tu secreto.
5. El payload por defecto de Grafana es su propio formato JSON (`alerts[]`, `commonLabels`, etc.), no el contrato de Vectora — usa un **Custom Payload / message template** si tu versión de Grafana lo soporta para emitir `{title, description, severity, url, external_id}` directamente, mapeando `alertname`/`summary` → `title`, `description`/`annotations` → `description`, la etiqueta `severity` de la alerta → `severity`, `generatorURL` → `url`, y `fingerprint` → `external_id` (el fingerprint de Grafana es estable durante todo el ciclo de vida de la alerta, exactamente lo que necesita la reentrega idempotente).

### PagerDuty — Custom Webhook (Extensions)

1. **Service → Integrations → Add a webhook**, o **Extensions → Add extension** → **Generic V3 Webhook** en la política de escalado/servicio que quieras reenviar.
2. URL del webhook: `https://<tu-backend>/webhook/observability`.
3. Los Generic Webhooks de PagerDuty no soportan headers personalizados de forma nativa — la mayoría de las configuraciones necesitan un pequeño relay (Cloudflare Worker, Lambda, etc.) que reciba el payload nativo de PagerDuty, añada el header `X-Webhook-Secret`, y remodele el cuerpo al contrato de Vectora.
4. Mapeo de campos del payload `incident` de PagerDuty: `incident.title` → `title`, `incident.description` o los detalles del evento que disparó la alerta → `description`, `incident.urgency` (`high` → `high`, `low` → `low`) o `incident.priority` → `severity`, `incident.html_url` → `url`, `incident.id` → `external_id`.

## Ver también

- [Automatización del Agente](../agent-automation) — programación, delegación y los demás disparadores de tareas en segundo plano por webhook
- [Usando el Workbench](../using-the-workbench) — la pestaña Tasks donde aparecen las tarjetas sincronizadas

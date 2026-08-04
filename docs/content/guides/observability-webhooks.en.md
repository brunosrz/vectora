---
title: Observability Webhooks
weight: 7
---

Vectora's webhook infrastructure (`backend/api/handlers/webhooks.py`) ships native support for a handful of providers (GitHub, GitLab, Slack, Linear, email). For alerting and observability tools — Sentry, Grafana, PagerDuty, and the rest of that space — there is no vendor-specific parser. Instead there is one generic endpoint with a fixed, documented payload contract: point your tool's outbound webhook at it, and adjust the payload to match the shape below.

This is a deliberate trade-off. A dedicated Sentry/Grafana/PagerDuty parser would need to track each vendor's payload shape as it evolves; a fixed contract never goes stale, at the cost of you doing the field mapping once in your alerting tool's webhook configuration.

## Endpoint

```
POST /webhook/observability
X-Webhook-Secret: <your secret>
Content-Type: application/json

{
  "title": "Error 500 in /checkout",
  "description": "NullPointerException in the payment gateway",
  "severity": "critical",
  "url": "https://sentry.io/issues/1",
  "external_id": "sentry-1"
}
```

| Field         | Required | Notes                                                                 |
|---------------|----------|------------------------------------------------------------------------|
| `title`       | yes      | Becomes the Kanban card's name.                                       |
| `external_id` | yes      | Idempotency key — a stable id from your alerting tool (alert/incident id). Redelivery of the same `external_id` updates the existing card instead of creating a duplicate. |
| `description` | no       | Becomes the card's instruction body (truncated to 2000 characters).   |
| `severity`    | no       | `critical` / `high` / `medium` / `low`. See mapping below.             |
| `url`         | no       | Link back to the alert in your tool, stored on the card.              |

Authentication is a static secret, not an HMAC signature: set `OBSERVABILITY_WEBHOOK_SECRET` on the backend and send it back in the `X-Webhook-Secret` header on every request. A missing or incorrect secret returns `401` before the payload is ever parsed. A malformed body, or a body missing `title`/`external_id`, returns `400`.

## Severity → Kanban status

The Kanban board has no native priority field, so severity maps to the card's initial status instead:

- `critical` / `high` → **triage** (needs immediate attention)
- `medium` / `low` (or missing/unrecognized) → **todo**

Redelivery re-evaluates severity and moves the card accordingly — an alert that started `critical` and later reports `low` in a follow-up payload moves out of triage.

## Turning the sync on

Like the GitHub Issues → Kanban sync, this is off by default. It activates when there is at least one enabled `webhook`-triggered background task whose `trigger_config` is `{"provider": "observability"}` — that task's session and workspace become the home for every card the sync creates. Without such a task, the endpoint still accepts and persists events (so nothing is lost while you're setting things up), but no card is created.

This runs entirely without the LLM: it's a deterministic insert-or-update against the same `vectora_background_tasks` table the rest of the Kanban model uses (`backend/scheduling/background_tasks.py::sync_observability_alert_to_kanban`), the same pattern the GitHub Issues sync (`sync_github_issue_to_kanban`) already established.

## Provider configuration examples

These are honest best-effort mappings — none of these tools speak Vectora's contract natively, so you're translating their outbound webhook payload into the shape above, typically via each tool's own "custom payload" or templating feature where available, or a lightweight relay otherwise.

### Sentry — Alert Rules → Webhook Action

1. **Settings → Alerts → Rules** → edit or create a rule.
2. Add an action of type **"Send a notification via an integration"** → **Webhook**, or use **Internal Integrations** (**Settings → Developer Settings → Custom Integrations**) to get a dedicated webhook URL with more control over the payload.
3. Point the webhook URL at `https://<your-backend>/webhook/observability`.
4. Set the `X-Webhook-Secret` header to your `OBSERVABILITY_WEBHOOK_SECRET` value (custom headers are available on Internal Integrations; plain Alert Rule webhooks may need a small relay if your Sentry plan doesn't support custom headers).
5. Map Sentry's payload fields to Vectora's: `event.title` → `title`, `event.culprit`/`event.message` → `description`, `event.level` (`fatal`/`error` → `critical`/`high`, `warning` → `medium`, `info`/`debug` → `low`) → `severity`, `url` → `url`, `event.event_id` or the issue id → `external_id`.

### Grafana Alerting — Contact Point (Webhook)

1. **Alerting → Contact points → Add contact point**.
2. Integration type: **Webhook**.
3. URL: `https://<your-backend>/webhook/observability`.
4. Under **Optional Webhook settings**, add a custom HTTP header `X-Webhook-Secret` with your secret.
5. Grafana's default webhook payload is its own JSON shape (`alerts[]`, `commonLabels`, etc.), not Vectora's contract — use a **Custom Payload / message template** if your Grafana version supports it to emit `{title, description, severity, url, external_id}` directly, mapping `alertname`/`summary` → `title`, `description`/`annotations` → `description`, the alert's `severity` label → `severity`, `generatorURL` → `url`, and `fingerprint` → `external_id` (Grafana's fingerprint is stable across the alert's lifecycle, which is exactly what idempotent redelivery needs).

### PagerDuty — Custom Webhook (Extensions)

1. **Service → Integrations → Add a webhook**, or **Extensions → Add extension** → **Generic V3 Webhook** on the escalation policy/service you want to forward.
2. Webhook URL: `https://<your-backend>/webhook/observability`.
3. PagerDuty's Generic Webhooks don't support custom headers out of the box — most setups need a small relay (Cloudflare Worker, Lambda, etc.) that receives PagerDuty's native payload, adds the `X-Webhook-Secret` header, and re-shapes the body to Vectora's contract.
4. Field mapping from PagerDuty's `incident` payload: `incident.title` → `title`, `incident.description` or the triggering event's details → `description`, `incident.urgency` (`high` → `high`, `low` → `low`) or `incident.priority` → `severity`, `incident.html_url` → `url`, `incident.id` → `external_id`.

## See also

- [Agent Automation](../agent-automation) — scheduling, delegation, and the other webhook-driven background task triggers
- [Using the Workbench](../using-the-workbench) — the Tasks tab where synced cards show up

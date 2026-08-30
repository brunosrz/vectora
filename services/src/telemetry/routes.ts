/**
 * telemetry/ — ingestão genérica de eventos do backend Python local
 * (crash/uso). Sem auth: Free não tem conta, e o dado aqui não é sensível
 * o bastante pra justificar exigir sessão — mas `source` é restrito a uma
 * allowlist e o payload é limitado por MAX_PAYLOAD_BYTES (mesma variável já
 * usada pelo gateway pra limitar tamanho de request).
 *
 * Sem CORS de propósito: chamada só server-to-server (backend Python local,
 * nunca browser) — mesmo padrão documentado em company/src/lib/services/
 * client.ts. Se algum dia um client rodando em browser precisar chamar isto
 * direto, precisa de CORS real, não confiar em same-origin implícito.
 */
import { Hono } from "hono";
import type { Env } from "../gateway/types";
import { enqueueJob } from "../lib/queue";

export const telemetry = new Hono<{ Bindings: Env }>();

const ALLOWED_SOURCES = new Set(["vectora-app", "vectora-desktop"]);

telemetry.post("/ingest", async (c) => {
  const maxBytes = parseInt(c.env.MAX_PAYLOAD_BYTES, 10);
  const contentLength = parseInt(c.req.header("content-length") ?? "0", 10);
  if (contentLength > maxBytes) {
    return c.json({ error: "payload_too_large" }, 413);
  }

  const body = await c.req.json<{
    source?: string;
    eventType?: string;
    payload?: unknown;
  }>();

  if (!body.source || !ALLOWED_SOURCES.has(body.source)) {
    return c.json({ error: "invalid_source" }, 400);
  }
  if (!body.eventType) {
    return c.json({ error: "event_type_required" }, 400);
  }

  await enqueueJob(c.env, {
    type: "telemetry_ingest",
    source: body.source,
    eventType: body.eventType,
    payload: body.payload ?? null,
  });

  return c.json({ ok: true });
});

/** Chamado pelo consumer da fila `vectora-jobs` (job `telemetry_ingest`). */
export async function recordTelemetryEvent(
  env: Env,
  event: { source: string; eventType: string; payload: unknown },
): Promise<void> {
  await env.DB.prepare(
    "INSERT INTO telemetry_events (id, source, event_type, payload) VALUES (?, ?, ?, ?)",
  )
    .bind(
      crypto.randomUUID(),
      event.source,
      event.eventType,
      JSON.stringify(event.payload),
    )
    .run();
}

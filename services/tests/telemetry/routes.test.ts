import { env } from "cloudflare:test";
import { describe, expect, it, vi, afterEach } from "vitest";
import { telemetry, recordTelemetryEvent } from "../../src/telemetry/routes";

afterEach(() => {
  vi.restoreAllMocks();
});

async function ingest(body: unknown, headers: Record<string, string> = {}) {
  const payload = JSON.stringify(body);
  return telemetry.request(
    "/ingest",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "content-length": String(new TextEncoder().encode(payload).length),
        ...headers,
      },
      body: payload,
    },
    env,
  );
}

describe("POST /telemetry/ingest", () => {
  it("enqueues a telemetry_ingest job for an allowed source", async () => {
    const sendSpy = vi.spyOn(env.JOBS_QUEUE, "send");

    const res = await ingest({
      source: "vectora-app",
      eventType: "crash",
      payload: { stack: "Traceback..." },
    });

    expect(res.status).toBe(200);
    expect(await res.json()).toEqual({ ok: true });
    expect(sendSpy).toHaveBeenCalledExactlyOnceWith({
      type: "telemetry_ingest",
      source: "vectora-app",
      eventType: "crash",
      payload: { stack: "Traceback..." },
    });
  });

  it("accepts vectora-desktop as a source too", async () => {
    const sendSpy = vi.spyOn(env.JOBS_QUEUE, "send");
    const res = await ingest({ source: "vectora-desktop", eventType: "boot" });
    expect(res.status).toBe(200);
    expect(sendSpy).toHaveBeenCalledExactlyOnceWith({
      type: "telemetry_ingest",
      source: "vectora-desktop",
      eventType: "boot",
      payload: null,
    });
  });

  it("rejects a source outside the allowlist", async () => {
    const res = await ingest({ source: "anything-goes", eventType: "x" });
    expect(res.status).toBe(400);
    expect(await res.json()).toEqual({ error: "invalid_source" });
  });

  it("rejects a missing source and a missing eventType", async () => {
    const missingSource = await ingest({ eventType: "crash" });
    expect(missingSource.status).toBe(400);
    expect(await missingSource.json()).toEqual({ error: "invalid_source" });

    const missingEventType = await ingest({ source: "vectora-app" });
    expect(missingEventType.status).toBe(400);
    expect(await missingEventType.json()).toEqual({
      error: "event_type_required",
    });
  });

  it("rejects a payload bigger than MAX_PAYLOAD_BYTES", async () => {
    const res = await ingest(
      { source: "vectora-app", eventType: "crash" },
      { "content-length": String(Number(env.MAX_PAYLOAD_BYTES) + 1) },
    );
    expect(res.status).toBe(413);
    expect(await res.json()).toEqual({ error: "payload_too_large" });
  });
});

describe("recordTelemetryEvent", () => {
  it("grava o evento em telemetry_events com o payload serializado", async () => {
    await recordTelemetryEvent(env, {
      source: "vectora-app",
      eventType: "crash",
      payload: { stack: "boom" },
    });

    const row = await env.DB.prepare(
      "SELECT source, event_type, payload FROM telemetry_events WHERE source = ? AND event_type = ?",
    )
      .bind("vectora-app", "crash")
      .first<{ source: string; event_type: string; payload: string }>();

    expect(row).toMatchObject({ source: "vectora-app", event_type: "crash" });
    expect(JSON.parse(row!.payload)).toEqual({ stack: "boom" });
  });

  it("aceita payload null", async () => {
    await recordTelemetryEvent(env, {
      source: "vectora-desktop",
      eventType: "boot",
      payload: null,
    });

    const row = await env.DB.prepare(
      "SELECT payload FROM telemetry_events WHERE source = ? AND event_type = ?",
    )
      .bind("vectora-desktop", "boot")
      .first<{ payload: string }>();

    expect(JSON.parse(row!.payload)).toBeNull();
  });
});

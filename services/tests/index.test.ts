import {
  createExecutionContext,
  createScheduledController,
  env,
  waitOnExecutionContext,
} from "cloudflare:test";
import { describe, expect, it } from "vitest";
import worker from "../src/index";

const itDO = env.TEST_IS_WINDOWS === "1" ? it.skip : it;

describe("fetch dispatch by hostname", () => {
  it("routes relay.vectora.chat to the relay handler (DO-free /oauth/token endpoint)", async () => {
    const ctx = createExecutionContext();
    const req = new Request("https://relay.vectora.chat/oauth/token", {
      method: "POST",
      headers: {
        Authorization: "Bearer test-oauth-secret",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ state: "s1", token: "tok" }),
    });
    const res = await worker.fetch(req, env, ctx);
    await waitOnExecutionContext(ctx);
    expect(res.status).toBe(200);
    expect(await res.json()).toEqual({ ok: true });
  });

  itDO("routes {token}.vectora.chat to the relay Durable Object", async () => {
    const ctx = createExecutionContext();
    const req = new Request("https://abc123.vectora.chat/health/abc123", {
      method: "GET",
    });
    const res = await worker.fetch(req, env, ctx);
    await waitOnExecutionContext(ctx);
    // A DO real recém-criada não tem cliente conectado — 200 com connected:false.
    expect(res.status).toBe(200);
  });

  it("routes update.vectora.company to the updates app", async () => {
    const ctx = createExecutionContext();
    const req = new Request("https://update.vectora.company/health");
    const res = await worker.fetch(req, env, ctx);
    await waitOnExecutionContext(ctx);
    expect(res.status).toBe(200);
    const body = await res.json<{ server: string }>();
    expect(body.server).toBe("vectora-services/updates");
  });

  it("routes any other host to the services app", async () => {
    const ctx = createExecutionContext();
    const req = new Request("https://services.vectora.company/health");
    const res = await worker.fetch(req, env, ctx);
    await waitOnExecutionContext(ctx);
    expect(res.status).toBe(200);
    const body = await res.json<{ server: string }>();
    expect(body.server).toBe("vectora-services");
  });
});

describe("scheduled()", () => {
  it("runs hardDeleteExpiredUsers via waitUntil", async () => {
    const userId = crypto.randomUUID();
    await env.DB.prepare(
      "INSERT INTO users (id, email, password_hash, soft_delete_at) VALUES (?, ?, ?, ?)",
    )
      .bind(
        userId,
        `${userId}@example.com`,
        "pbkdf2$1$AA==$AA==",
        new Date(Date.now() - 31 * 24 * 60 * 60 * 1000).toISOString(),
      )
      .run();

    const ctx = createExecutionContext();
    await worker.scheduled!(createScheduledController(), env, ctx);
    await waitOnExecutionContext(ctx);

    const gone = await env.DB.prepare("SELECT id FROM users WHERE id = ?")
      .bind(userId)
      .first();
    expect(gone).toBeNull();
  });
});

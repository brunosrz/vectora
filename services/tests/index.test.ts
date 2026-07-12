import {
  createExecutionContext,
  createScheduledController,
  env,
  waitOnExecutionContext,
} from "cloudflare:test";
import { describe, expect, it, vi } from "vitest";
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

  it("routes an unrecognized host to the services app", async () => {
    const ctx = createExecutionContext();
    const req = new Request("https://services.vectora.company/health");
    const res = await worker.fetch(req, env, ctx);
    await waitOnExecutionContext(ctx);
    expect(res.status).toBe(200);
    const body = await res.json<{ server: string }>();
    expect(body.server).toBe("vectora-services");
  });

  it("routes /download to the merged updates app on the default host", async () => {
    const ctx = createExecutionContext();
    // Corpo "unknown channel" só vem do updates app — prova que a rota
    // chegou lá, sem precisar simular um download completo.
    const req = new Request(
      "https://services.vectora.company/download/latest/win-x64.exe",
    );
    const res = await worker.fetch(req, env, ctx);
    await waitOnExecutionContext(ctx);
    expect(res.status).toBe(404);
    expect(await res.text()).toBe("unknown channel");
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
  it("enqueues a gdpr_delete_user job via waitUntil for each expired user", async () => {
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

    const sendSpy = vi.spyOn(env.JOBS_QUEUE, "send");
    const ctx = createExecutionContext();
    await worker.scheduled!(createScheduledController(), env, ctx);
    await waitOnExecutionContext(ctx);

    expect(sendSpy).toHaveBeenCalledWith({
      type: "gdpr_delete_user",
      userId,
    });

    // scheduled() só enfileira — o usuário continua no D1 até o consumer
    // da fila chamar hardDeleteOneUser.
    const stillThere = await env.DB.prepare("SELECT id FROM users WHERE id = ?")
      .bind(userId)
      .first();
    expect(stillThere).not.toBeNull();
  });

  it("expires gift subscriptions whose current_period_end has passed, leaving lifetime gifts untouched", async () => {
    const expiredUserId = crypto.randomUUID();
    const lifetimeUserId = crypto.randomUUID();
    for (const id of [expiredUserId, lifetimeUserId]) {
      await env.DB.prepare(
        "INSERT INTO users (id, email, password_hash) VALUES (?, ?, ?)",
      )
        .bind(id, `${id}@example.com`, "pbkdf2$1$AA==$AA==")
        .run();
    }
    await env.DB.prepare(
      "INSERT INTO subscriptions (id, user_id, tier, status, provider, current_period_end) VALUES (?, ?, 'pro', 'active', 'gift', ?)",
    )
      .bind(
        crypto.randomUUID(),
        expiredUserId,
        new Date(Date.now() - 1000).toISOString(),
      )
      .run();
    await env.DB.prepare(
      "INSERT INTO subscriptions (id, user_id, tier, status, provider, current_period_end) VALUES (?, ?, 'pro', 'active', 'gift', NULL)",
    )
      .bind(crypto.randomUUID(), lifetimeUserId)
      .run();

    const ctx = createExecutionContext();
    await worker.scheduled!(createScheduledController(), env, ctx);
    await waitOnExecutionContext(ctx);

    const expired = await env.DB.prepare(
      "SELECT status, tier FROM subscriptions WHERE user_id = ?",
    )
      .bind(expiredUserId)
      .first<{ status: string; tier: string }>();
    expect(expired).toEqual({ status: "expired", tier: "free" });

    const lifetime = await env.DB.prepare(
      "SELECT status, tier FROM subscriptions WHERE user_id = ?",
    )
      .bind(lifetimeUserId)
      .first<{ status: string; tier: string }>();
    expect(lifetime).toEqual({ status: "active", tier: "pro" });
  });
});

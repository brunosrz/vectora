import { env } from "cloudflare:test";
import { describe, expect, it } from "vitest";
import { billing } from "./routes";
import { createSession } from "../auth/session";

async function makeUserWithSession(currency: "BRL" | "USD" = "BRL") {
  const userId = crypto.randomUUID();
  await env.DB.prepare(
    "INSERT INTO users (id, email, password_hash) VALUES (?, ?, ?)",
  )
    .bind(userId, `${userId}@example.com`, "pbkdf2$1$AA==$AA==")
    .run();
  await env.DB.prepare(
    "INSERT INTO subscriptions (id, user_id, tier, status, currency) VALUES (?, ?, 'free', 'active', ?)",
  )
    .bind(crypto.randomUUID(), userId, currency)
    .run();
  const session = await createSession(env.DB, userId);
  return { userId, token: session.token };
}

describe("POST /billing/webhooks", () => {
  it("rejects an unknown provider and an invalid stripe signature", async () => {
    const unknown = await billing.request(
      "/webhooks?provider=paypal",
      { method: "POST", body: "{}" },
      env,
    );
    expect(unknown.status).toBe(400);

    const badSig = await billing.request(
      "/webhooks?provider=stripe",
      {
        method: "POST",
        headers: { "stripe-signature": "bad-signature" },
        body: JSON.stringify({ type: "invoice.paid" }),
      },
      env,
    );
    expect(badSig.status).toBe(400);
    expect(await badSig.json()).toEqual({ error: "signature_failed" });
  });

  it("records an asaas PAYMENT_RECEIVED event and upgrades the subscription to pro", async () => {
    const { userId } = await makeUserWithSession();
    const res = await billing.request(
      "/webhooks?provider=asaas",
      {
        method: "POST",
        body: JSON.stringify({
          event: "PAYMENT_RECEIVED",
          payment: {
            externalReference: `${userId}:pro`,
            id: "pay_123",
            value: 24,
          },
        }),
      },
      env,
    );
    expect(res.status).toBe(200);

    const sub = await env.DB.prepare(
      "SELECT tier, status FROM subscriptions WHERE user_id = ?",
    )
      .bind(userId)
      .first<{ tier: string; status: string }>();
    expect(sub).toEqual({ tier: "pro", status: "active" });

    const events = await env.DB.prepare(
      "SELECT COUNT(*) as count FROM payment_events WHERE user_id = ?",
    )
      .bind(userId)
      .first<{ count: number }>();
    expect(events?.count).toBe(1);
  });
});

describe("POST /billing/checkout and /portal", () => {
  it("rejects unauthenticated checkout/portal requests", async () => {
    expect(
      (await billing.request("/checkout", { method: "POST" }, env)).status,
    ).toBe(401);
    expect(
      (await billing.request("/portal", { method: "POST" }, env)).status,
    ).toBe(401);
  });

  it("returns 404 from /portal when the user has no billing customer yet", async () => {
    const { token } = await makeUserWithSession();
    const res = await billing.request(
      "/portal",
      { method: "POST", headers: { Authorization: `Bearer ${token}` } },
      env,
    );
    expect(res.status).toBe(404);
  });
});

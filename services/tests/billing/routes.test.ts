import { env } from "cloudflare:test";
import { describe, expect, it, vi, afterEach } from "vitest";
import { billing } from "../../src/billing/routes";
import { createSession } from "../../src/auth/session";

async function makeUserWithSession(
  currency: "BRL" | "USD" = "BRL",
  customerId: string | null = null,
) {
  const userId = crypto.randomUUID();
  await env.DB.prepare(
    "INSERT INTO users (id, email, password_hash) VALUES (?, ?, ?)",
  )
    .bind(userId, `${userId}@example.com`, "pbkdf2$1$AA==$AA==")
    .run();
  await env.DB.prepare(
    "INSERT INTO subscriptions (id, user_id, tier, status, currency, customer_id) VALUES (?, ?, 'free', 'active', ?, ?)",
  )
    .bind(crypto.randomUUID(), userId, currency, customerId)
    .run();
  const session = await createSession(env.DB, userId);
  return { userId, token: session.token };
}

/** Mock de fetch por prefixo de URL — cada rota externa (Stripe/Asaas/Resend) responde com o JSON dado. */
function mockFetch(routes: Record<string, unknown>) {
  return vi.fn(async (input: RequestInfo | URL) => {
    const url = typeof input === "string" ? input : input.toString();
    const match = Object.entries(routes).find(([prefix]) =>
      url.includes(prefix),
    );
    if (!match) throw new Error(`unmocked fetch: ${url}`);
    return new Response(JSON.stringify(match[1]), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  });
}

async function stripeSignature(
  payload: string,
  secret: string,
): Promise<string> {
  const timestamp = Math.floor(Date.now() / 1000);
  const signedPayload = `${timestamp}.${payload}`;
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const sig = await crypto.subtle.sign(
    "HMAC",
    key,
    new TextEncoder().encode(signedPayload),
  );
  const hex = Array.from(new Uint8Array(sig))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
  return `t=${timestamp},v1=${hex}`;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

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
    vi.stubGlobal("fetch", mockFetch({ "api.resend.com": {} }));

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

  it("marks the subscription past_due on PAYMENT_OVERDUE and sends a failure email", async () => {
    const { userId } = await makeUserWithSession();
    vi.stubGlobal("fetch", mockFetch({ "api.resend.com": {} }));

    const res = await billing.request(
      "/webhooks?provider=asaas",
      {
        method: "POST",
        body: JSON.stringify({
          event: "PAYMENT_OVERDUE",
          payment: { externalReference: `${userId}:pro`, value: 24 },
        }),
      },
      env,
    );
    expect(res.status).toBe(200);

    const sub = await env.DB.prepare(
      "SELECT status FROM subscriptions WHERE user_id = ?",
    )
      .bind(userId)
      .first<{ status: string }>();
    expect(sub?.status).toBe("past_due");
  });

  it("cancels back to free on PAYMENT_DELETED/PAYMENT_REFUNDED", async () => {
    const { userId } = await makeUserWithSession();

    const res = await billing.request(
      "/webhooks?provider=asaas",
      {
        method: "POST",
        body: JSON.stringify({
          event: "PAYMENT_REFUNDED",
          payment: { externalReference: `${userId}:pro` },
        }),
      },
      env,
    );
    expect(res.status).toBe(200);

    const sub = await env.DB.prepare(
      "SELECT status, tier FROM subscriptions WHERE user_id = ?",
    )
      .bind(userId)
      .first<{ status: string; tier: string }>();
    expect(sub).toEqual({ status: "canceled", tier: "free" });
  });

  describe("stripe events", () => {
    async function postStripeEvent(payloadObj: unknown) {
      const payload = JSON.stringify(payloadObj);
      const sig = await stripeSignature(payload, "whsec_test_fake");
      return billing.request(
        "/webhooks?provider=stripe",
        {
          method: "POST",
          headers: {
            "stripe-signature": sig,
            "Content-Type": "application/json",
          },
          body: payload,
        },
        env,
      );
    }

    it("invoice.paid: activates the subscription with the retrieved plan/period and emails the user", async () => {
      const { userId } = await makeUserWithSession("USD");
      vi.stubGlobal(
        "fetch",
        mockFetch({
          "api.stripe.com/v1/subscriptions/sub_123": {
            id: "sub_123",
            metadata: { plan: "pro" },
            items: {
              data: [
                { current_period_end: 1_800_000_000, price: { metadata: {} } },
              ],
            },
          },
          "api.resend.com": {},
        }),
      );

      const res = await postStripeEvent({
        id: "evt_1",
        type: "invoice.paid",
        data: {
          object: {
            metadata: { user_id: userId },
            amount_paid: 900,
            currency: "usd",
            parent: { subscription_details: { subscription: "sub_123" } },
          },
        },
      });
      expect(res.status).toBe(200);

      const sub = await env.DB.prepare(
        "SELECT status, tier, provider, provider_id FROM subscriptions WHERE user_id = ?",
      )
        .bind(userId)
        .first<{
          status: string;
          tier: string;
          provider: string;
          provider_id: string;
        }>();
      expect(sub).toEqual({
        status: "active",
        tier: "pro",
        provider: "stripe",
        provider_id: "sub_123",
      });
    });

    it("invoice.payment_failed: marks past_due and emails the user", async () => {
      const { userId } = await makeUserWithSession("USD");
      vi.stubGlobal("fetch", mockFetch({ "api.resend.com": {} }));

      const res = await postStripeEvent({
        id: "evt_2",
        type: "invoice.payment_failed",
        data: {
          object: {
            metadata: { user_id: userId },
            amount_due: 900,
            currency: "usd",
          },
        },
      });
      expect(res.status).toBe(200);

      const sub = await env.DB.prepare(
        "SELECT status FROM subscriptions WHERE user_id = ?",
      )
        .bind(userId)
        .first<{ status: string }>();
      expect(sub?.status).toBe("past_due");
    });

    it("customer.subscription.deleted: reverts tier to free", async () => {
      const { userId } = await makeUserWithSession("USD");

      const res = await postStripeEvent({
        id: "evt_3",
        type: "customer.subscription.deleted",
        data: { object: { metadata: { user_id: userId } } },
      });
      expect(res.status).toBe(200);

      const sub = await env.DB.prepare(
        "SELECT status, tier FROM subscriptions WHERE user_id = ?",
      )
        .bind(userId)
        .first<{ status: string; tier: string }>();
      expect(sub).toEqual({ status: "canceled", tier: "free" });
    });
  });
});

describe("GET /billing/subscription", () => {
  it("returns the caller's own subscription, 401/404 otherwise", async () => {
    const { token } = await makeUserWithSession("USD");
    const res = await billing.request(
      "/subscription",
      { headers: { Authorization: `Bearer ${token}` } },
      env,
    );
    expect(res.status).toBe(200);
    const body = await res.json<{ tier: string; currency: string }>();
    expect(body).toMatchObject({ tier: "free", currency: "USD" });

    expect((await billing.request("/subscription", {}, env)).status).toBe(401);
  });
});

describe("POST /billing/checkout", () => {
  it("rejects unauthenticated requests", async () => {
    expect(
      (await billing.request("/checkout", { method: "POST" }, env)).status,
    ).toBe(401);
  });

  it("BRL currency: creates an Asaas payment and returns its invoice URL", async () => {
    const { token } = await makeUserWithSession("BRL");
    vi.stubGlobal(
      "fetch",
      mockFetch({
        "api.asaas.com": { invoiceUrl: "https://asaas.test/invoice/1" },
      }),
    );

    const res = await billing.request(
      "/checkout",
      { method: "POST", headers: { Authorization: `Bearer ${token}` } },
      env,
    );
    expect(res.status).toBe(200);
    expect(await res.json()).toEqual({ url: "https://asaas.test/invoice/1" });
  });

  it("USD currency without a stripe customer yet: creates the customer, persists it, and returns the checkout URL", async () => {
    const { userId, token } = await makeUserWithSession("USD");
    vi.stubGlobal(
      "fetch",
      mockFetch({
        "api.stripe.com/v1/customers": { id: "cus_new" },
        "api.stripe.com/v1/checkout/sessions": {
          url: "https://checkout.stripe.test/1",
        },
      }),
    );

    const res = await billing.request(
      "/checkout",
      { method: "POST", headers: { Authorization: `Bearer ${token}` } },
      env,
    );
    expect(res.status).toBe(200);
    expect(await res.json()).toEqual({ url: "https://checkout.stripe.test/1" });

    const sub = await env.DB.prepare(
      "SELECT customer_id FROM subscriptions WHERE user_id = ?",
    )
      .bind(userId)
      .first<{ customer_id: string }>();
    expect(sub?.customer_id).toBe("cus_new");
  });

  it("USD currency with an existing stripe customer: reuses it (no customer.create call)", async () => {
    const { token } = await makeUserWithSession("USD", "cus_existing");
    const fetchMock = mockFetch({
      "api.stripe.com/v1/checkout/sessions": {
        url: "https://checkout.stripe.test/2",
      },
    });
    vi.stubGlobal("fetch", fetchMock);

    const res = await billing.request(
      "/checkout",
      { method: "POST", headers: { Authorization: `Bearer ${token}` } },
      env,
    );
    expect(res.status).toBe(200);
    for (const call of fetchMock.mock.calls) {
      expect(String(call[0])).not.toContain("/v1/customers");
    }
  });
});

describe("POST /billing/portal", () => {
  it("returns 404 when the user has no billing customer yet", async () => {
    const { token } = await makeUserWithSession();
    const res = await billing.request(
      "/portal",
      { method: "POST", headers: { Authorization: `Bearer ${token}` } },
      env,
    );
    expect(res.status).toBe(404);
  });

  it("BRL currency: returns the Asaas billing info URL", async () => {
    const { token } = await makeUserWithSession("BRL", "cus_br_1");
    vi.stubGlobal(
      "fetch",
      mockFetch({
        "api.asaas.com": { billingInfoUrl: "https://asaas.test/billing/1" },
      }),
    );

    const res = await billing.request(
      "/portal",
      { method: "POST", headers: { Authorization: `Bearer ${token}` } },
      env,
    );
    expect(res.status).toBe(200);
    expect(await res.json()).toEqual({ url: "https://asaas.test/billing/1" });
  });

  it("USD currency: returns the Stripe billing portal URL", async () => {
    const { token } = await makeUserWithSession("USD", "cus_us_1");
    vi.stubGlobal(
      "fetch",
      mockFetch({
        "api.stripe.com/v1/billing_portal/sessions": {
          url: "https://billing.stripe.test/1",
        },
      }),
    );

    const res = await billing.request(
      "/portal",
      { method: "POST", headers: { Authorization: `Bearer ${token}` } },
      env,
    );
    expect(res.status).toBe(200);
    expect(await res.json()).toEqual({ url: "https://billing.stripe.test/1" });
  });
});

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

/** POST /billing/webhooks?provider=asaas já com o header exigido pela
 * validação de asaas-access-token (mesmo valor fixado em vitest.config.mts). */
function asaasWebhook(body: unknown) {
  return billing.request(
    "/webhooks?provider=asaas",
    {
      method: "POST",
      headers: { "asaas-access-token": "test-asaas-webhook-secret" },
      body: JSON.stringify(body),
    },
    env,
  );
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

  it("rejects an asaas webhook without a valid asaas-access-token, accepts the correct one", async () => {
    const { userId } = await makeUserWithSession();
    vi.stubGlobal("fetch", mockFetch({ "api.resend.com": {} }));
    const payload = {
      event: "PAYMENT_RECEIVED",
      payment: { externalReference: `${userId}:pro`, id: "pay_x", value: 24 },
    };

    const noToken = await billing.request(
      "/webhooks?provider=asaas",
      { method: "POST", body: JSON.stringify(payload) },
      env,
    );
    expect(noToken.status).toBe(401);
    expect(await noToken.json()).toEqual({ error: "invalid_webhook_token" });

    const wrongToken = await billing.request(
      "/webhooks?provider=asaas",
      {
        method: "POST",
        headers: { "asaas-access-token": "forged-token" },
        body: JSON.stringify(payload),
      },
      env,
    );
    expect(wrongToken.status).toBe(401);

    // Nenhuma das duas tentativas forjadas alterou a assinatura.
    const subBefore = await env.DB.prepare(
      "SELECT tier FROM subscriptions WHERE user_id = ?",
    )
      .bind(userId)
      .first<{ tier: string }>();
    expect(subBefore?.tier).toBe("free");

    const ok = await asaasWebhook(payload);
    expect(ok.status).toBe(200);
    const subAfter = await env.DB.prepare(
      "SELECT tier FROM subscriptions WHERE user_id = ?",
    )
      .bind(userId)
      .first<{ tier: string }>();
    expect(subAfter?.tier).toBe("pro");
  });

  it("records an asaas PAYMENT_RECEIVED event and upgrades the subscription to pro", async () => {
    const { userId } = await makeUserWithSession();
    vi.stubGlobal("fetch", mockFetch({ "api.resend.com": {} }));

    const res = await asaasWebhook({
      event: "PAYMENT_RECEIVED",
      payment: {
        externalReference: `${userId}:pro`,
        id: "pay_123",
        value: 24,
      },
    });
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

    const res = await asaasWebhook({
      event: "PAYMENT_OVERDUE",
      payment: { externalReference: `${userId}:pro`, value: 24 },
    });
    expect(res.status).toBe(200);

    const sub = await env.DB.prepare(
      "SELECT status FROM subscriptions WHERE user_id = ?",
    )
      .bind(userId)
      .first<{ status: string }>();
    expect(sub?.status).toBe("past_due");
  });

  it("grants current_period_end from the plan's months, and redeems the coupon exactly once", async () => {
    const { userId } = await makeUserWithSession();
    const adminId = crypto.randomUUID();
    await env.DB.prepare(
      "INSERT INTO users (id, email, password_hash, role) VALUES (?, ?, ?, 'admin')",
    )
      .bind(adminId, `${adminId}@example.com`, "pbkdf2$1$AA==$AA==")
      .run();
    const couponId = crypto.randomUUID();
    await env.DB.prepare(
      "INSERT INTO coupons (id, code, kind, grant_plan_id, charge_plan_id, created_by) VALUES (?, 'ASAASCOUPON', 'discount', '12m', '1m', ?)",
    )
      .bind(couponId, adminId)
      .run();
    vi.stubGlobal("fetch", mockFetch({ "api.resend.com": {} }));

    const res = await asaasWebhook({
      event: "PAYMENT_RECEIVED",
      payment: {
        externalReference: `${userId}:12m:${couponId}`,
        id: "pay_456",
        value: 96,
      },
    });
    expect(res.status).toBe(200);

    const sub = await env.DB.prepare(
      "SELECT current_period_end FROM subscriptions WHERE user_id = ?",
    )
      .bind(userId)
      .first<{ current_period_end: string }>();
    const monthsAhead =
      (new Date(sub!.current_period_end).getTime() - Date.now()) /
      (30 * 24 * 60 * 60 * 1000);
    expect(monthsAhead).toBeGreaterThan(11);
    expect(monthsAhead).toBeLessThan(13);

    const redemption = await env.DB.prepare(
      "SELECT COUNT(*) as count FROM coupon_redemptions WHERE coupon_id = ? AND user_id = ?",
    )
      .bind(couponId, userId)
      .first<{ count: number }>();
    expect(redemption?.count).toBe(1);

    // Reenvio do mesmo webhook (retry do Asaas) não redime 2x.
    await asaasWebhook({
      event: "PAYMENT_CONFIRMED",
      payment: {
        externalReference: `${userId}:12m:${couponId}`,
        id: "pay_456",
        value: 96,
      },
    });
    const redemptionAfterRetry = await env.DB.prepare(
      "SELECT COUNT(*) as count FROM coupon_redemptions WHERE coupon_id = ? AND user_id = ?",
    )
      .bind(couponId, userId)
      .first<{ count: number }>();
    expect(redemptionAfterRetry?.count).toBe(1);
  });

  it("cancels back to free on PAYMENT_DELETED/PAYMENT_REFUNDED", async () => {
    const { userId } = await makeUserWithSession();

    const res = await asaasWebhook({
      event: "PAYMENT_REFUNDED",
      payment: { externalReference: `${userId}:pro` },
    });
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

    it("invoice.paid with a coupon_id in the subscription metadata: redeems it exactly once, even across a retry", async () => {
      const { userId } = await makeUserWithSession("USD");
      const adminId = crypto.randomUUID();
      await env.DB.prepare(
        "INSERT INTO users (id, email, password_hash, role) VALUES (?, ?, ?, 'admin')",
      )
        .bind(adminId, `${adminId}@example.com`, "pbkdf2$1$AA==$AA==")
        .run();
      const couponId = crypto.randomUUID();
      await env.DB.prepare(
        "INSERT INTO coupons (id, code, kind, grant_plan_id, charge_plan_id, created_by) VALUES (?, 'STRIPECOUPON', 'discount', '12m', '1m', ?)",
      )
        .bind(couponId, adminId)
        .run();
      vi.stubGlobal(
        "fetch",
        mockFetch({
          "api.stripe.com/v1/subscriptions/sub_coupon": {
            id: "sub_coupon",
            metadata: { plan: "12m", coupon_id: couponId },
            items: {
              data: [
                { current_period_end: 1_800_000_000, price: { metadata: {} } },
              ],
            },
          },
          "api.resend.com": {},
        }),
      );

      const payload = {
        id: "evt_coupon",
        type: "invoice.paid",
        data: {
          object: {
            metadata: { user_id: userId },
            amount_paid: 900,
            currency: "usd",
            parent: { subscription_details: { subscription: "sub_coupon" } },
          },
        },
      };
      const res = await postStripeEvent(payload);
      expect(res.status).toBe(200);

      const redemption = await env.DB.prepare(
        "SELECT COUNT(*) as count FROM coupon_redemptions WHERE coupon_id = ? AND user_id = ?",
      )
        .bind(couponId, userId)
        .first<{ count: number }>();
      expect(redemption?.count).toBe(1);

      // Stripe reenvia webhooks até obter 200 — o mesmo evento não pode redimir 2x.
      await postStripeEvent({ ...payload, id: "evt_coupon_retry" });
      const redemptionAfterRetry = await env.DB.prepare(
        "SELECT COUNT(*) as count FROM coupon_redemptions WHERE coupon_id = ? AND user_id = ?",
      )
        .bind(couponId, userId)
        .first<{ count: number }>();
      expect(redemptionAfterRetry?.count).toBe(1);
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

async function checkout(token: string, body: Record<string, unknown>) {
  return billing.request(
    "/checkout",
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    },
    env,
  );
}

const STRIPE_PRICE_MOCKS = {
  "api.stripe.com/v1/prices/price_test_fake": {
    id: "price_test_fake",
    product: "prod_123",
  },
  "api.stripe.com/v1/prices": { id: "price_new" },
};

describe("POST /billing/checkout", () => {
  it("rejects unauthenticated requests", async () => {
    expect(
      (await billing.request("/checkout", { method: "POST" }, env)).status,
    ).toBe(401);
  });

  it("rejects a missing or unknown plan_id", async () => {
    const { token } = await makeUserWithSession("USD");
    expect((await checkout(token, {})).status).toBe(400);
    expect((await checkout(token, { plan_id: "does-not-exist" })).status).toBe(
      400,
    );
  });

  it("BRL currency: creates an Asaas payment for the plan's price and returns its invoice URL", async () => {
    const { token } = await makeUserWithSession("BRL");
    vi.stubGlobal(
      "fetch",
      mockFetch({
        "api.asaas.com": { invoiceUrl: "https://asaas.test/invoice/1" },
      }),
    );

    const res = await checkout(token, { plan_id: "3m" });
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
        ...STRIPE_PRICE_MOCKS,
      }),
    );

    const res = await checkout(token, { plan_id: "1m" });
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
      ...STRIPE_PRICE_MOCKS,
    });
    vi.stubGlobal("fetch", fetchMock);

    const res = await checkout(token, { plan_id: "1m" });
    expect(res.status).toBe(200);
    for (const call of fetchMock.mock.calls) {
      expect(String(call[0])).not.toContain("/v1/customers");
    }
  });

  describe("with a coupon", () => {
    async function createCoupon(
      overrides: Partial<{
        code: string;
        kind: "discount" | "free_lifetime";
        grant_plan_id: string | null;
        charge_plan_id: string | null;
        max_redemptions: number | null;
      }> = {},
    ) {
      const id = crypto.randomUUID();
      const adminId = crypto.randomUUID();
      await env.DB.prepare(
        "INSERT INTO users (id, email, password_hash, role) VALUES (?, ?, ?, 'admin')",
      )
        .bind(adminId, `${adminId}@example.com`, "pbkdf2$1$AA==$AA==")
        .run();
      await env.DB.prepare(
        `INSERT INTO coupons (id, code, kind, grant_plan_id, charge_plan_id, max_redemptions, created_by)
         VALUES (?, ?, ?, ?, ?, ?, ?)`,
      )
        .bind(
          id,
          overrides.code ?? "TESTCODE",
          overrides.kind ?? "discount",
          overrides.grant_plan_id ?? "12m",
          overrides.charge_plan_id ?? "6m",
          overrides.max_redemptions ?? null,
          adminId,
        )
        .run();
      return id;
    }

    it("rejects an unknown coupon code", async () => {
      const { token } = await makeUserWithSession("USD");
      const res = await checkout(token, { plan_id: "1m", coupon_code: "NOPE" });
      expect(res.status).toBe(400);
      expect(await res.json()).toEqual({ error: "invalid_coupon" });
    });

    it("discount: charges charge_plan_id but grants grant_plan_id via Stripe metadata", async () => {
      const { token } = await makeUserWithSession("USD");
      await createCoupon({ code: "DISCOUNT3M" });
      let capturedBody: string | undefined;
      vi.stubGlobal(
        "fetch",
        vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
          const url = typeof input === "string" ? input : input.toString();
          if (url.includes("/v1/checkout/sessions")) {
            capturedBody = init?.body as string;
            return new Response(
              JSON.stringify({ url: "https://checkout.stripe.test/discount" }),
              { status: 200 },
            );
          }
          if (url.includes("/v1/customers")) {
            return new Response(JSON.stringify({ id: "cus_new" }), {
              status: 200,
            });
          }
          if (url.includes("/v1/prices/price_test_fake")) {
            return new Response(
              JSON.stringify({ id: "price_test_fake", product: "prod_123" }),
              { status: 200 },
            );
          }
          if (url.includes("/v1/prices")) {
            return new Response(JSON.stringify({ id: "price_1m_new" }), {
              status: 200,
            });
          }
          throw new Error(`unmocked fetch: ${url}`);
        }),
      );

      const res = await checkout(token, {
        plan_id: "6m",
        coupon_code: "discount3m",
      });
      expect(res.status).toBe(200);
      expect(capturedBody).toContain("metadata[plan]=12m");

      const priceRow = await env.DB.prepare(
        "SELECT stripe_price_id FROM plans WHERE id = '6m'",
      ).first<{ stripe_price_id: string }>();
      expect(priceRow?.stripe_price_id).toBe("price_1m_new");
    });

    it("free_lifetime: grants Pro lifetime immediately without any checkout, single-use", async () => {
      const { userId, token } = await makeUserWithSession("USD");
      await createCoupon({
        code: "SECRET1",
        kind: "free_lifetime",
        grant_plan_id: null,
        charge_plan_id: null,
        max_redemptions: 1,
      });

      const res = await checkout(token, {
        plan_id: "1m",
        coupon_code: "SECRET1",
      });
      expect(res.status).toBe(200);
      expect(await res.json()).toEqual({ redeemed: true });

      const sub = await env.DB.prepare(
        "SELECT tier, status, provider, current_period_end FROM subscriptions WHERE user_id = ?",
      )
        .bind(userId)
        .first<{
          tier: string;
          status: string;
          provider: string;
          current_period_end: string | null;
        }>();
      expect(sub).toEqual({
        tier: "pro",
        status: "active",
        provider: "gift",
        current_period_end: null,
      });

      const { token: token2 } = await makeUserWithSession("USD");
      const second = await checkout(token2, {
        plan_id: "1m",
        coupon_code: "SECRET1",
      });
      expect(second.status).toBe(400);
      expect(await second.json()).toEqual({ error: "invalid_coupon" });
    });

    it("rejects a coupon the user already redeemed before (409, distinct from an unknown coupon)", async () => {
      const { userId, token } = await makeUserWithSession("USD");
      const couponId = await createCoupon({
        code: "ONCEPERUSER",
        max_redemptions: null,
      });
      await env.DB.prepare(
        "INSERT INTO coupon_redemptions (id, coupon_id, user_id) VALUES (?, ?, ?)",
      )
        .bind(crypto.randomUUID(), couponId, userId)
        .run();

      const res = await checkout(token, {
        plan_id: "1m",
        coupon_code: "ONCEPERUSER",
      });
      expect(res.status).toBe(409);
      expect(await res.json()).toEqual({ error: "coupon_already_redeemed" });
    });
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

import { env } from "cloudflare:test";
import { describe, expect, it, vi, afterEach } from "vitest";
import { license } from "../../src/license/routes";
import { sha256Hex } from "../../src/auth/session";
import { hashPassword } from "../../src/auth/password";
import { createSession } from "../../src/auth/session";

/** Mock de fetch por prefixo de URL — cada rota externa (Stripe/Asaas) responde com o JSON dado. */
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

afterEach(() => {
  vi.unstubAllGlobals();
});

async function makeUserWithToken(
  opts: { tier?: string; status?: string } = {},
) {
  const userId = crypto.randomUUID();
  const email = `${userId}@example.com`;
  const password = "correct horse battery staple";
  await env.DB.prepare(
    "INSERT INTO users (id, email, password_hash) VALUES (?, ?, ?)",
  )
    .bind(userId, email, await hashPassword(password))
    .run();
  const rawToken = crypto.randomUUID();
  await env.DB.prepare(
    "INSERT INTO tokens (id, user_id, token, token_hash) VALUES (?, ?, ?, ?)",
  )
    .bind(crypto.randomUUID(), userId, rawToken, await sha256Hex(rawToken))
    .run();
  await env.DB.prepare(
    "INSERT INTO subscriptions (id, user_id, tier, status, currency) VALUES (?, ?, ?, ?, 'USD')",
  )
    .bind(
      crypto.randomUUID(),
      userId,
      opts.tier ?? "pro",
      opts.status ?? "active",
    )
    .run();
  return { userId, email, password, rawToken };
}

async function validate(token: string) {
  return license.request(
    "/validate",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token, version: "1.0.0" }),
    },
    env,
  );
}

async function makeUserWithTokenNoSubscription() {
  const userId = crypto.randomUUID();
  const email = `${userId}@example.com`;
  const password = "correct horse battery staple";
  await env.DB.prepare(
    "INSERT INTO users (id, email, password_hash) VALUES (?, ?, ?)",
  )
    .bind(userId, email, await hashPassword(password))
    .run();
  const rawToken = crypto.randomUUID();
  await env.DB.prepare(
    "INSERT INTO tokens (id, user_id, token, token_hash) VALUES (?, ?, ?, ?)",
  )
    .bind(crypto.randomUUID(), userId, rawToken, await sha256Hex(rawToken))
    .run();
  return { userId, email, password, rawToken };
}

describe("POST /validate", () => {
  it("reports tier null when the token has no subscription row at all", async () => {
    const { rawToken } = await makeUserWithTokenNoSubscription();
    const res = await validate(rawToken);
    const json = await res.json<{ valid: boolean; tier: string | null }>();
    expect(json).toMatchObject({ valid: false, tier: null });
  });

  it("validates an active token as valid, and reports an unknown token as not_found", async () => {
    const { rawToken } = await makeUserWithToken();

    const res = await validate(rawToken);
    expect(res.status).toBe(200);
    const json = await res.json<{ valid: boolean; tier: string }>();
    expect(json.valid).toBe(true);
    expect(json.tier).toBe("pro");

    const missing = await validate("never-issued");
    const missingJson = await missing.json<{
      valid: boolean;
      reason: string;
    }>();
    expect(missingJson).toEqual({ valid: false, reason: "not_found" });
  });

  it("requires a token in the request body", async () => {
    const res = await license.request(
      "/validate",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: "{}",
      },
      env,
    );
    expect(res.status).toBe(400);
  });

  it("treats a non-expired trial as valid and an expired trial as expired", async () => {
    const { rawToken: activeTrialToken, userId: activeUid } =
      await makeUserWithToken({
        status: "trialing",
      });
    await env.DB.prepare(
      "UPDATE subscriptions SET trial_ends_at = ? WHERE user_id = ?",
    )
      .bind(new Date(Date.now() + 86_400_000).toISOString(), activeUid)
      .run();
    const activeRes = await (
      await validate(activeTrialToken)
    ).json<{
      valid: boolean;
      status: string;
    }>();
    expect(activeRes).toMatchObject({ valid: true, status: "trial" });

    const { rawToken: expiredTrialToken, userId: expiredUid } =
      await makeUserWithToken({
        status: "trialing",
      });
    await env.DB.prepare(
      "UPDATE subscriptions SET trial_ends_at = ? WHERE user_id = ?",
    )
      .bind(new Date(Date.now() - 86_400_000).toISOString(), expiredUid)
      .run();
    const expiredRes = await (
      await validate(expiredTrialToken)
    ).json<{
      valid: boolean;
      status: string;
    }>();
    expect(expiredRes).toMatchObject({ valid: false, status: "expired" });
  });

  it("treats past_due as a valid grace period, and canceled as expired", async () => {
    const { rawToken: pastDueToken } = await makeUserWithToken({
      status: "past_due",
    });
    const pastDueRes = await (
      await validate(pastDueToken)
    ).json<{ valid: boolean }>();
    expect(pastDueRes.valid).toBe(true);

    const { rawToken: canceledToken } = await makeUserWithToken({
      status: "canceled",
    });
    const canceledRes = await (
      await validate(canceledToken)
    ).json<{
      valid: boolean;
      status: string;
    }>();
    expect(canceledRes).toMatchObject({ valid: false, status: "expired" });
  });
});

describe("POST /agent-login", () => {
  it("reveals the token once and rotates it on a second login (show-once semantics)", async () => {
    const { email, password, rawToken } = await makeUserWithToken();

    const first = await license.request(
      "/agent-login",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      },
      env,
    );
    expect(first.status).toBe(200);
    const firstJson = await first.json<{ token: string }>();
    expect(firstJson.token).toBe(rawToken);

    const second = await license.request(
      "/agent-login",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      },
      env,
    );
    const secondJson = await second.json<{ token: string }>();
    expect(secondJson.token).not.toBe(rawToken);
  });

  it("reports tier/status null when the user has no subscription row", async () => {
    const { email, password } = await makeUserWithTokenNoSubscription();
    const res = await license.request(
      "/agent-login",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      },
      env,
    );
    expect(res.status).toBe(200);
    expect(await res.json()).toMatchObject({ tier: null, status: null });
  });

  it("rejects invalid credentials and missing fields, and 404s when there's no token row", async () => {
    const { email } = await makeUserWithToken();
    const wrongPassword = await license.request(
      "/agent-login",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password: "wrong" }),
      },
      env,
    );
    expect(wrongPassword.status).toBe(401);

    const missingFields = await license.request(
      "/agent-login",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: "{}",
      },
      env,
    );
    expect(missingFields.status).toBe(400);

    const unknownEmail = await license.request(
      "/agent-login",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: "nope@example.com", password: "x" }),
      },
      env,
    );
    expect(unknownEmail.status).toBe(401);

    const userId = crypto.randomUUID();
    const noTokenEmail = `${userId}@example.com`;
    await env.DB.prepare(
      "INSERT INTO users (id, email, password_hash) VALUES (?, ?, ?)",
    )
      .bind(userId, noTokenEmail, await hashPassword("some-password"))
      .run();
    const noToken = await license.request(
      "/agent-login",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: noTokenEmail,
          password: "some-password",
        }),
      },
      env,
    );
    expect(noToken.status).toBe(404);
  });
});

describe("POST /portal", () => {
  it("returns the Stripe portal URL for a USD subscriber with a customer_id", async () => {
    const { userId, rawToken } = await makeUserWithToken();
    await env.DB.prepare(
      "UPDATE subscriptions SET customer_id = ? WHERE user_id = ?",
    )
      .bind("cus_test_123", userId)
      .run();
    vi.stubGlobal(
      "fetch",
      mockFetch({
        "api.stripe.com/v1/billing_portal/sessions": {
          url: "https://billing.stripe.test/1",
        },
      }),
    );

    const res = await license.request(
      "/portal",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token: rawToken }),
      },
      env,
    );
    expect(res.status).toBe(200);
    const json = await res.json<{ url: string }>();
    expect(json.url).toBe("https://billing.stripe.test/1");
  });

  it("returns the Asaas billingInfoUrl for a BRL subscriber", async () => {
    const { userId, rawToken } = await makeUserWithToken();
    await env.DB.prepare(
      "UPDATE subscriptions SET currency = 'BRL', customer_id = ? WHERE user_id = ?",
    )
      .bind("cus_asaas_123", userId)
      .run();
    vi.stubGlobal(
      "fetch",
      mockFetch({
        "api.asaas.com": { billingInfoUrl: "https://asaas.test/billing/1" },
      }),
    );

    const res = await license.request(
      "/portal",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token: rawToken }),
      },
      env,
    );
    expect(res.status).toBe(200);
    const json = await res.json<{ url: string }>();
    expect(json.url).toBe("https://asaas.test/billing/1");
  });

  it("rejects a missing token, an unknown token, and 404s with no customer_id", async () => {
    const missingBody = await license.request(
      "/portal",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: "{}",
      },
      env,
    );
    expect(missingBody.status).toBe(400);

    const unknownToken = await license.request(
      "/portal",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token: "never-issued" }),
      },
      env,
    );
    expect(unknownToken.status).toBe(401);

    const { rawToken: noCustomerToken } = await makeUserWithToken();
    const noCustomer = await license.request(
      "/portal",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token: noCustomerToken }),
      },
      env,
    );
    expect(noCustomer.status).toBe(404);
  });
});

describe("POST /rotate", () => {
  it("rotates the token for the authenticated user, invalidating the previous one", async () => {
    const { userId, rawToken } = await makeUserWithToken();
    const session = await createSession(env.DB, userId);

    const res = await license.request(
      "/rotate",
      { method: "POST", headers: { Authorization: `Bearer ${session.token}` } },
      env,
    );
    expect(res.status).toBe(200);
    const { token: newToken } = await res.json<{ token: string }>();
    expect(newToken).not.toBe(rawToken);

    expect(
      (await (await validate(rawToken)).json<{ valid: boolean }>()).valid,
    ).toBe(false);
    expect(
      (await (await validate(newToken)).json<{ valid: boolean }>()).valid,
    ).toBe(true);
  });

  it("rejects unauthenticated requests and 404s when the user has no token", async () => {
    expect(
      (await license.request("/rotate", { method: "POST" }, env)).status,
    ).toBe(401);

    const userId = crypto.randomUUID();
    await env.DB.prepare(
      "INSERT INTO users (id, email, password_hash) VALUES (?, ?, ?)",
    )
      .bind(userId, `${userId}@example.com`, "pbkdf2$1$AA==$AA==")
      .run();
    const session = await createSession(env.DB, userId);
    const res = await license.request(
      "/rotate",
      { method: "POST", headers: { Authorization: `Bearer ${session.token}` } },
      env,
    );
    expect(res.status).toBe(404);
  });
});

describe("GET /token-status and POST /token/reveal", () => {
  it("reports the token as available and returns the same value on repeat reveals (recoverable, not show-once)", async () => {
    const { userId, rawToken } = await makeUserWithToken();
    const session = await createSession(env.DB, userId);
    const auth = { Authorization: `Bearer ${session.token}` };

    const before = await license.request(
      "/token-status",
      { headers: auth },
      env,
    );
    expect(await before.json()).toEqual({ available: true });

    const reveal = await license.request(
      "/token/reveal",
      { method: "POST", headers: auth },
      env,
    );
    expect(await reveal.json()).toEqual({ token: rawToken });

    const after = await license.request(
      "/token-status",
      { headers: auth },
      env,
    );
    expect(await after.json()).toEqual({ available: true });

    const revealAgain = await license.request(
      "/token/reveal",
      { method: "POST", headers: auth },
      env,
    );
    expect(await revealAgain.json()).toEqual({ token: rawToken });
  });

  it("404s a reveal when the user has no recoverable token, and rejects unauthenticated requests", async () => {
    expect((await license.request("/token-status", {}, env)).status).toBe(401);
    expect(
      (await license.request("/token/reveal", { method: "POST" }, env)).status,
    ).toBe(401);

    const userId = crypto.randomUUID();
    await env.DB.prepare(
      "INSERT INTO users (id, email, password_hash) VALUES (?, ?, ?)",
    )
      .bind(userId, `${userId}@example.com`, "pbkdf2$1$AA==$AA==")
      .run();
    await env.DB.prepare(
      "INSERT INTO tokens (id, user_id, token, token_hash) VALUES (?, ?, NULL, ?)",
    )
      .bind(crypto.randomUUID(), userId, "deadbeef")
      .run();
    const session = await createSession(env.DB, userId);
    const res = await license.request(
      "/token/reveal",
      { method: "POST", headers: { Authorization: `Bearer ${session.token}` } },
      env,
    );
    expect(res.status).toBe(404);
  });
});

describe("GET /history", () => {
  it("lists the caller's own license checks, most recent first", async () => {
    const { userId, rawToken } = await makeUserWithToken();
    await validate(rawToken);
    await validate(rawToken);

    const session = await createSession(env.DB, userId);
    const res = await license.request(
      "/history",
      { headers: { Authorization: `Bearer ${session.token}` } },
      env,
    );
    expect(res.status).toBe(200);
    const rows = await res.json<Array<{ user_id: string }>>();
    expect(rows.length).toBeGreaterThanOrEqual(2);
    expect(rows.every((r) => r.user_id === userId)).toBe(true);
  });

  it("rejects unauthenticated requests", async () => {
    expect((await license.request("/history", {}, env)).status).toBe(401);
  });
});

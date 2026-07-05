import { env } from "cloudflare:test";
import { describe, expect, it, vi } from "vitest";
import { admin } from "../../src/admin/routes";
import { createSession } from "../../src/auth/session";

async function createUser(
  role: "user" | "admin" = "user",
  overrides: Partial<{ email: string; full_name: string }> = {},
) {
  const userId = crypto.randomUUID();
  await env.DB.prepare(
    "INSERT INTO users (id, email, password_hash, full_name, role) VALUES (?, ?, ?, ?, ?)",
  )
    .bind(
      userId,
      overrides.email ?? `${userId}@example.com`,
      "pbkdf2$1$AA==$AA==",
      overrides.full_name ?? "Test User",
      role,
    )
    .run();
  await env.DB.prepare(
    "INSERT INTO subscriptions (id, user_id, tier, status) VALUES (?, ?, 'free', 'active')",
  )
    .bind(crypto.randomUUID(), userId)
    .run();
  const session = await createSession(env.DB, userId);
  return { userId, token: session.token };
}

function authed(token: string, init: RequestInit = {}) {
  return {
    ...init,
    headers: { ...init.headers, Authorization: `Bearer ${token}` },
  };
}

describe("admin routes — access control", () => {
  it("rejects a non-admin (403) and an unauthenticated caller (403)", async () => {
    const { token } = await createUser("user");
    expect((await admin.request("/users", authed(token), env)).status).toBe(
      403,
    );
    expect((await admin.request("/users", {}, env)).status).toBe(403);
  });
});

describe("GET /admin/users", () => {
  it("lists users with their subscription, admin only", async () => {
    const { token: adminToken } = await createUser("admin");
    const { userId } = await createUser("user", {
      email: "listed@example.com",
    });

    const res = await admin.request("/users", authed(adminToken), env);
    expect(res.status).toBe(200);
    const body = await res.json<{
      users: Array<{ id: string; email: string }>;
    }>();
    expect(body.users.some((u) => u.id === userId)).toBe(true);
  });
});

describe("POST /admin/coupons", () => {
  it("creates a discount coupon, rejects a duplicate code, and validates required fields", async () => {
    const { token } = await createUser("admin");

    const res = await admin.request(
      "/coupons",
      authed(token, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          code: "newcode",
          kind: "discount",
          grant_plan_id: "3m",
          charge_plan_id: "1m",
        }),
      }),
      env,
    );
    expect(res.status).toBe(200);
    expect((await res.json<{ code: string }>()).code).toBe("NEWCODE");

    const dup = await admin.request(
      "/coupons",
      authed(token, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          code: "newcode",
          kind: "discount",
          grant_plan_id: "3m",
          charge_plan_id: "1m",
        }),
      }),
      env,
    );
    expect(dup.status).toBe(409);

    const missingPlans = await admin.request(
      "/coupons",
      authed(token, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code: "other", kind: "discount" }),
      }),
      env,
    );
    expect(missingPlans.status).toBe(400);

    const invalidKind = await admin.request(
      "/coupons",
      authed(token, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code: "other2", kind: "bogus" }),
      }),
      env,
    );
    expect(invalidKind.status).toBe(400);
  });

  it("creates a free_lifetime coupon without plan fields", async () => {
    const { token } = await createUser("admin");
    const res = await admin.request(
      "/coupons",
      authed(token, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code: "SECRETONE", kind: "free_lifetime" }),
      }),
      env,
    );
    expect(res.status).toBe(200);
  });
});

describe("GET /admin/coupons and POST /:id/deactivate", () => {
  it("lists coupons and deactivates one by id, 404 for unknown id", async () => {
    const { token } = await createUser("admin");
    await admin.request(
      "/coupons",
      authed(token, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          code: "TODEACTIVATE",
          kind: "discount",
          grant_plan_id: "3m",
          charge_plan_id: "1m",
        }),
      }),
      env,
    );

    const list = await admin.request("/coupons", authed(token), env);
    expect(list.status).toBe(200);
    const { coupons } = await list.json<{
      coupons: Array<{ id: string; code: string; active: number }>;
    }>();
    const created = coupons.find((c) => c.code === "TODEACTIVATE")!;
    expect(created.active).toBe(1);

    const deactivate = await admin.request(
      `/coupons/${created.id}/deactivate`,
      authed(token, { method: "POST" }),
      env,
    );
    expect(deactivate.status).toBe(200);

    const notFound = await admin.request(
      "/coupons/does-not-exist/deactivate",
      authed(token, { method: "POST" }),
      env,
    );
    expect(notFound.status).toBe(404);
  });
});

describe("POST /admin/gifts", () => {
  it("rejects an invalid email", async () => {
    const { token } = await createUser("admin");
    const res = await admin.request(
      "/gifts",
      authed(token, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: "not-an-email" }),
      }),
      env,
    );
    expect(res.status).toBe(400);
  });

  it("for an email without an account yet: records a pending gift and enqueues the email", async () => {
    const { token } = await createUser("admin", { full_name: "Bruno" });
    const sendSpy = vi.spyOn(env.EMAIL_QUEUE, "send");

    const res = await admin.request(
      "/gifts",
      authed(token, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: "future-user@example.com" }),
      }),
      env,
    );
    expect(res.status).toBe(200);
    expect(await res.json<{ claimed: boolean }>()).toMatchObject({
      claimed: false,
    });
    expect(sendSpy).toHaveBeenCalledExactlyOnceWith(
      expect.objectContaining({ to: "future-user@example.com" }),
    );

    const gift = await env.DB.prepare(
      "SELECT status, duration_months FROM gifts WHERE email = ?",
    )
      .bind("future-user@example.com")
      .first<{ status: string; duration_months: number | null }>();
    expect(gift).toEqual({ status: "pending", duration_months: null });
    sendSpy.mockRestore();
  });

  it("for an existing account: grants Pro immediately with the given duration and marks the gift claimed", async () => {
    const { token } = await createUser("admin");
    const { userId } = await createUser("user", {
      email: "already-has-account@example.com",
    });

    const res = await admin.request(
      "/gifts",
      authed(token, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: "already-has-account@example.com",
          duration_months: 6,
        }),
      }),
      env,
    );
    expect(res.status).toBe(200);
    expect(await res.json<{ claimed: boolean }>()).toMatchObject({
      claimed: true,
    });

    const sub = await env.DB.prepare(
      "SELECT tier, status, provider, current_period_end FROM subscriptions WHERE user_id = ?",
    )
      .bind(userId)
      .first<{
        tier: string;
        status: string;
        provider: string;
        current_period_end: string;
      }>();
    expect(sub?.tier).toBe("pro");
    expect(sub?.provider).toBe("gift");
    expect(sub?.current_period_end).not.toBeNull();

    const gift = await env.DB.prepare(
      "SELECT status, claimed_user_id FROM gifts WHERE email = ?",
    )
      .bind("already-has-account@example.com")
      .first<{ status: string; claimed_user_id: string }>();
    expect(gift).toEqual({ status: "claimed", claimed_user_id: userId });
  });

  it("lists gifts already given", async () => {
    const { token } = await createUser("admin");
    await admin.request(
      "/gifts",
      authed(token, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: "listed-gift@example.com" }),
      }),
      env,
    );

    const res = await admin.request("/gifts", authed(token), env);
    expect(res.status).toBe(200);
    const { gifts } = await res.json<{ gifts: Array<{ email: string }> }>();
    expect(gifts.some((g) => g.email === "listed-gift@example.com")).toBe(true);
  });
});

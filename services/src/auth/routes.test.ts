import { env } from "cloudflare:test";
import { describe, expect, it } from "vitest";
import { auth } from "./routes";
import { sha256Hex } from "./session";

function signupBody(overrides: Partial<Record<string, unknown>> = {}) {
  return {
    name: "Ada Lovelace",
    email: `ada-${crypto.randomUUID()}@example.com`,
    password: "correct horse battery staple",
    country: "INTL",
    turnstileToken: "test-token",
    ...overrides,
  };
}

async function post(
  path: string,
  body: unknown,
  headers: Record<string, string> = {},
) {
  return auth.request(
    path,
    {
      method: "POST",
      headers: { "Content-Type": "application/json", ...headers },
      body: JSON.stringify(body),
    },
    env,
  );
}

describe("POST /signup", () => {
  it("creates the user + free subscription + show-once token, and rejects a duplicate email", async () => {
    const body = signupBody();
    const res = await post("/signup", body);
    expect(res.status).toBe(200);
    expect(await res.json()).toEqual({
      needsConfirmation: true,
      email: body.email,
    });

    const user = await env.DB.prepare(
      "SELECT id, email_verified FROM users WHERE email = ?",
    )
      .bind(body.email)
      .first<{ id: string; email_verified: number }>();
    expect(user?.email_verified).toBe(0);

    const sub = await env.DB.prepare(
      "SELECT tier, status FROM subscriptions WHERE user_id = ?",
    )
      .bind(user!.id)
      .first<{ tier: string; status: string }>();
    expect(sub).toEqual({ tier: "free", status: "active" });

    const token = await env.DB.prepare(
      "SELECT token FROM tokens WHERE user_id = ?",
    )
      .bind(user!.id)
      .first<{ token: string | null }>();
    expect(token?.token).not.toBeNull();

    const dup = await post("/signup", signupBody({ email: body.email }));
    expect(dup.status).toBe(409);
    expect(await dup.json()).toEqual({ error: "email_taken" });
  });

  it("rejects invalid email, short password, and missing turnstile token in the same request shape", async () => {
    expect(
      (await post("/signup", signupBody({ email: "not-an-email" }))).status,
    ).toBe(400);
    expect(
      (await post("/signup", signupBody({ password: "short" }))).status,
    ).toBe(400);
    const res = await post(
      "/signup",
      signupBody({ turnstileToken: undefined }),
    );
    expect(res.status).toBe(400);
    expect(await res.json()).toEqual({ error: "turnstile_required" });
  });
});

describe("POST /verify", () => {
  async function createUnverifiedUserWithToken() {
    const userId = crypto.randomUUID();
    await env.DB.prepare(
      "INSERT INTO users (id, email, password_hash) VALUES (?, ?, ?)",
    )
      .bind(userId, `${userId}@example.com`, "pbkdf2$1$AA==$AA==")
      .run();
    const rawToken = crypto.randomUUID();
    const tokenHash = await sha256Hex(rawToken);
    await env.DB.prepare(
      "INSERT INTO email_verifications (id, user_id, token_hash, purpose, expires_at) VALUES (?, ?, ?, 'verify_email', ?)",
    )
      .bind(
        crypto.randomUUID(),
        userId,
        tokenHash,
        new Date(Date.now() + 60_000).toISOString(),
      )
      .run();
    return { userId, rawToken };
  }

  it("marks the user verified, opens a session, and rejects reuse of the same token", async () => {
    const { userId, rawToken } = await createUnverifiedUserWithToken();

    const res = await post("/verify", { token: rawToken });
    expect(res.status).toBe(200);
    const json = await res.json<{ session_token: string }>();
    expect(json.session_token).toBeTruthy();

    const user = await env.DB.prepare(
      "SELECT email_verified FROM users WHERE id = ?",
    )
      .bind(userId)
      .first<{ email_verified: number }>();
    expect(user?.email_verified).toBe(1);

    const reuse = await post("/verify", { token: rawToken });
    expect(reuse.status).toBe(410);
    expect(await reuse.json()).toEqual({ error: "token_already_used" });
  });

  it("rejects an unknown token and an expired token", async () => {
    expect((await post("/verify", { token: "never-issued" })).status).toBe(404);

    const { userId } = await createUnverifiedUserWithToken();
    const expiredToken = crypto.randomUUID();
    await env.DB.prepare(
      "INSERT INTO email_verifications (id, user_id, token_hash, purpose, expires_at) VALUES (?, ?, ?, 'verify_email', ?)",
    )
      .bind(
        crypto.randomUUID(),
        userId,
        await sha256Hex(expiredToken),
        new Date(Date.now() - 1000).toISOString(),
      )
      .run();
    const res = await post("/verify", { token: expiredToken });
    expect(res.status).toBe(410);
    expect(await res.json()).toEqual({ error: "token_expired" });
  });
});

describe("POST /login and GET /me", () => {
  it("logs in a verified user and resolves /me with the session token, rejecting bad credentials", async () => {
    const body = signupBody();
    await post("/signup", body);
    const userRow = await env.DB.prepare("SELECT id FROM users WHERE email = ?")
      .bind(body.email)
      .first<{ id: string }>();
    await env.DB.prepare("UPDATE users SET email_verified = 1 WHERE id = ?")
      .bind(userRow!.id)
      .run();

    const wrongPassword = await post("/login", {
      email: body.email,
      password: "wrong",
    });
    expect(wrongPassword.status).toBe(401);

    const login = await post("/login", {
      email: body.email,
      password: body.password,
    });
    expect(login.status).toBe(200);
    const { session_token: sessionToken } = await login.json<{
      session_token: string;
    }>();

    const me = await auth.request(
      "/me",
      { headers: { Authorization: `Bearer ${sessionToken}` } },
      env,
    );
    expect(me.status).toBe(200);
    expect((await me.json<{ email: string }>()).email).toBe(body.email);

    const unauthenticated = await auth.request("/me", {}, env);
    expect(unauthenticated.status).toBe(401);
  });

  it("rejects login for an unverified user", async () => {
    const body = signupBody();
    await post("/signup", body);
    const res = await post("/login", {
      email: body.email,
      password: body.password,
    });
    expect(res.status).toBe(403);
    expect(await res.json()).toEqual({ error: "email_not_verified" });
  });
});

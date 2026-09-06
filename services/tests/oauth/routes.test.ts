import { env } from "cloudflare:test";
import { describe, expect, it, vi, afterEach } from "vitest";
import { oauth } from "../../src/oauth/routes";
import { createSession } from "../../src/auth/session";

afterEach(() => {
  vi.unstubAllGlobals();
});

async function makeUserWithSession(withToken: boolean) {
  const userId = crypto.randomUUID();
  await env.DB.prepare(
    "INSERT INTO users (id, email, password_hash) VALUES (?, ?, ?)",
  )
    .bind(userId, `${userId}@example.com`, "pbkdf2$1$AA==$AA==")
    .run();
  await env.DB.prepare(
    "INSERT INTO tokens (id, user_id, token, token_hash) VALUES (?, ?, ?, ?)",
  )
    .bind(crypto.randomUUID(), userId, withToken ? "raw-token" : null, "hash")
    .run();
  const session = await createSession(env.DB, userId);
  return session.token;
}

describe("POST /oauth/device", () => {
  it("rejects unauthenticated requests and requests missing state", async () => {
    expect(
      (
        await oauth.request(
          "/device",
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: "{}",
          },
          env,
        )
      ).status,
    ).toBe(401);

    const token = await makeUserWithSession(true);
    const missingState = await oauth.request(
      "/device",
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: "{}",
      },
      env,
    );
    expect(missingState.status).toBe(400);
  });

  it("returns no_token when the show-once token was already revealed", async () => {
    const token = await makeUserWithSession(false);
    const res = await oauth.request(
      "/device",
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ state: "abc" }),
      },
      env,
    );
    expect(res.status).toBe(409);
    expect(await res.json()).toEqual({ error: "no_token" });
  });

  it("forwards the token to gateway/oauth/token and returns ok on success", async () => {
    const token = await makeUserWithSession(true);
    const fetchMock = vi.fn(async (url: string, init: RequestInit) => {
      expect(url).toBe("https://gateway.vectora.chat/oauth/token");
      expect(init.headers).toMatchObject({
        Authorization: "Bearer test-oauth-secret",
      });
      return new Response(JSON.stringify({ ok: true }));
    });
    vi.stubGlobal("fetch", fetchMock);

    const res = await oauth.request(
      "/device",
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ state: "abc" }),
      },
      env,
    );
    expect(res.status).toBe(200);
    expect(await res.json()).toEqual({ ok: true });
  });

  it("returns a 502 when the gateway call fails", async () => {
    const token = await makeUserWithSession(true);
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(null, { status: 500 })),
    );

    const res = await oauth.request(
      "/device",
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ state: "abc" }),
      },
      env,
    );
    expect(res.status).toBe(502);
    expect(await res.json()).toEqual({ error: "gateway_error" });
  });
});

describe("OAuth broker de integrações", () => {
  it("rejeita state curto e redirect fora de vectora.chat", async () => {
    const originalId = (env as unknown as Record<string, string | undefined>)
      .GITHUB_OAUTH_CLIENT_ID;
    const originalSecret = (
      env as unknown as Record<string, string | undefined>
    ).GITHUB_OAUTH_CLIENT_SECRET;
    const runtimeEnv = env as unknown as Record<string, string | undefined>;
    runtimeEnv.GITHUB_OAUTH_CLIENT_ID = "company-client";
    runtimeEnv.GITHUB_OAUTH_CLIENT_SECRET = "company-secret";
    const short = await oauth.request(
      "/integrations/github/start?state=short&return_to=https%3A%2F%2Fabc.vectora.chat%2Fauth%2Fgithub%2Fcallback",
      {},
      env,
    );
    expect(short.status).toBe(400);
    const invalidRedirect = await oauth.request(
      `/integrations/github/start?state=${"a".repeat(32)}&return_to=https%3A%2F%2Fevil.example%2Fcallback`,
      {},
      env,
    );
    expect(invalidRedirect.status).toBe(400);
    runtimeEnv.GITHUB_OAUTH_CLIENT_ID = originalId;
    runtimeEnv.GITHUB_OAUTH_CLIENT_SECRET = originalSecret;
  });

  it("exige o segredo de aplicação no polling do resultado", async () => {
    const state = "a".repeat(32);
    const response = await oauth.request(
      `/integrations/github/result/${state}`,
      {},
      env,
    );
    expect(response.status).toBe(401);
  });
});

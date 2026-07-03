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

  it("forwards the token to relay/oauth/token and returns ok on success", async () => {
    const token = await makeUserWithSession(true);
    const fetchMock = vi.fn(async (url: string, init: RequestInit) => {
      expect(url).toBe("https://relay.vectora.chat/oauth/token");
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

  it("returns a 502 when the relay call fails", async () => {
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
    expect(await res.json()).toEqual({ error: "relay_error" });
  });
});

import { env } from "cloudflare:test";
import { describe, expect, it } from "vitest";
import { license } from "./routes";
import { sha256Hex } from "../auth/session";
import { hashPassword } from "../auth/password";

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

describe("POST /validate", () => {
  it("validates an active token as valid, and reports an unknown token as not_found", async () => {
    const { rawToken } = await makeUserWithToken();

    const res = await license.request(
      "/validate",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token: rawToken, version: "1.0.0" }),
      },
      env,
    );
    expect(res.status).toBe(200);
    const json = await res.json<{ valid: boolean; tier: string }>();
    expect(json.valid).toBe(true);
    expect(json.tier).toBe("pro");

    const missing = await license.request(
      "/validate",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token: "never-issued" }),
      },
      env,
    );
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

  it("rejects invalid credentials", async () => {
    const { email } = await makeUserWithToken();
    const res = await license.request(
      "/agent-login",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password: "wrong" }),
      },
      env,
    );
    expect(res.status).toBe(401);
  });
});

import { env } from "cloudflare:test";
import { describe, expect, it } from "vitest";
import { oauth } from "./routes";
import { createSession } from "../auth/session";

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
});

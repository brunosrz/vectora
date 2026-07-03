import { env } from "cloudflare:test";
import { describe, expect, it } from "vitest";
import { profile } from "./routes";
import { createSession } from "../auth/session";

async function makeUserWithSession() {
  const userId = crypto.randomUUID();
  await env.DB.prepare(
    "INSERT INTO users (id, email, password_hash) VALUES (?, ?, ?)",
  )
    .bind(userId, `${userId}@example.com`, "pbkdf2$1$AA==$AA==")
    .run();
  const session = await createSession(env.DB, userId);
  return { userId, token: session.token };
}

describe("POST /profile/update", () => {
  it("updates allowed fields and rejects an unauthenticated request", async () => {
    const { userId, token } = await makeUserWithSession();

    const res = await profile.request(
      "/update",
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ full_name: "Grace Hopper", language: "en" }),
      },
      env,
    );
    expect(res.status).toBe(200);

    const row = await env.DB.prepare(
      "SELECT full_name, language FROM users WHERE id = ?",
    )
      .bind(userId)
      .first<{ full_name: string; language: string }>();
    expect(row).toEqual({ full_name: "Grace Hopper", language: "en" });

    const unauth = await profile.request(
      "/update",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: "{}",
      },
      env,
    );
    expect(unauth.status).toBe(401);
  });

  it("rejects an invalid full_name and an invalid country", async () => {
    const { token } = await makeUserWithSession();

    const tooShort = await profile.request(
      "/update",
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ full_name: "A" }),
      },
      env,
    );
    expect(tooShort.status).toBe(400);

    const badCountry = await profile.request(
      "/update",
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ country: "XX" }),
      },
      env,
    );
    expect(badCountry.status).toBe(400);
  });
});

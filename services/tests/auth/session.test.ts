import { env } from "cloudflare:test";
import { describe, expect, it } from "vitest";
import {
  bearerToken,
  createSession,
  resolveSession,
  revokeSession,
  sha256Hex,
} from "../../src/auth/session";

async function makeUser(): Promise<string> {
  const id = crypto.randomUUID();
  await env.DB.prepare(
    "INSERT INTO users (id, email, password_hash) VALUES (?, ?, ?)",
  )
    .bind(id, `${id}@example.com`, "pbkdf2$1$AA==$AA==")
    .run();
  return id;
}

describe("sha256Hex", () => {
  it("hashes deterministically to hex", async () => {
    const hash = await sha256Hex("hello");
    expect(hash).toBe(
      "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824",
    );
  });
});

describe("bearerToken", () => {
  it("extracts the token from an Authorization header, or returns null if absent/malformed", () => {
    const withToken = new Request("https://x.test", {
      headers: { Authorization: "Bearer abc123" },
    });
    expect(bearerToken(withToken)).toBe("abc123");

    const noHeader = new Request("https://x.test");
    expect(bearerToken(noHeader)).toBeNull();

    const malformed = new Request("https://x.test", {
      headers: { Authorization: "Basic abc123" },
    });
    expect(bearerToken(malformed)).toBeNull();
  });
});

describe("createSession/resolveSession/revokeSession", () => {
  it("creates a session that resolves to the owning user, and stops resolving after revoke", async () => {
    const userId = await makeUser();
    const session = await createSession(env.DB, userId);

    expect(await resolveSession(env.DB, session.token)).toBe(userId);

    await revokeSession(env.DB, session.token);
    expect(await resolveSession(env.DB, session.token)).toBeNull();
  });

  it("returns null for a null, unknown, or expired token", async () => {
    const userId = await makeUser();
    expect(await resolveSession(env.DB, null)).toBeNull();
    expect(await resolveSession(env.DB, "never-issued-token")).toBeNull();

    const expiredId = crypto.randomUUID();
    const tokenHash = await sha256Hex("expired-token");
    await env.DB.prepare(
      "INSERT INTO sessions (id, user_id, token_hash, expires_at) VALUES (?, ?, ?, ?)",
    )
      .bind(
        expiredId,
        userId,
        tokenHash,
        new Date(Date.now() - 1000).toISOString(),
      )
      .run();
    expect(await resolveSession(env.DB, "expired-token")).toBeNull();
  });
});

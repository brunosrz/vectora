import { env } from "cloudflare:test";
import { describe, expect, it } from "vitest";
import { gdpr, hardDeleteExpiredUsers } from "./routes";
import { createSession } from "../auth/session";

async function makeUserWithSession() {
  const userId = crypto.randomUUID();
  await env.DB.prepare(
    "INSERT INTO users (id, email, full_name, password_hash) VALUES (?, ?, ?, ?)",
  )
    .bind(userId, `${userId}@example.com`, "Ada Lovelace", "pbkdf2$1$AA==$AA==")
    .run();
  const session = await createSession(env.DB, userId);
  return { userId, token: session.token };
}

describe("POST /gdpr/export", () => {
  it("writes a JSON export to R2 and only the owner can download it", async () => {
    const { token } = await makeUserWithSession();
    const other = await makeUserWithSession();

    const res = await gdpr.request(
      "/export",
      { method: "POST", headers: { Authorization: `Bearer ${token}` } },
      env,
    );
    expect(res.status).toBe(200);
    const { url } = await res.json<{ url: string }>();
    const key = new URL(url).pathname.replace(/^.*\/export\//, "");

    const download = await gdpr.request(
      `/export/${key}`,
      { headers: { Authorization: `Bearer ${token}` } },
      env,
    );
    expect(download.status).toBe(200);
    const payload = await download.json<{ profile: { full_name: string } }>();
    expect(payload.profile.full_name).toBe("Ada Lovelace");

    const forbidden = await gdpr.request(
      `/export/${key}`,
      { headers: { Authorization: `Bearer ${other.token}` } },
      env,
    );
    expect(forbidden.status).toBe(403);
  });

  it("rejects unauthenticated export/delete requests", async () => {
    expect(
      (await gdpr.request("/export", { method: "POST" }, env)).status,
    ).toBe(401);
    expect(
      (await gdpr.request("/delete", { method: "POST" }, env)).status,
    ).toBe(401);
  });
});

describe("POST /gdpr/delete + hardDeleteExpiredUsers", () => {
  it("soft-deletes now and hard-deletes only once the retention window has passed", async () => {
    const { userId, token } = await makeUserWithSession();

    const res = await gdpr.request(
      "/delete",
      { method: "POST", headers: { Authorization: `Bearer ${token}` } },
      env,
    );
    expect(res.status).toBe(200);

    const softDeleted = await env.DB.prepare(
      "SELECT soft_delete_at FROM users WHERE id = ?",
    )
      .bind(userId)
      .first<{ soft_delete_at: string | null }>();
    expect(softDeleted?.soft_delete_at).not.toBeNull();

    const deletedNow = await hardDeleteExpiredUsers(env);
    expect(deletedNow).toBe(0);

    await env.DB.prepare("UPDATE users SET soft_delete_at = ? WHERE id = ?")
      .bind(
        new Date(Date.now() - 31 * 24 * 60 * 60 * 1000).toISOString(),
        userId,
      )
      .run();

    const deletedExpired = await hardDeleteExpiredUsers(env);
    expect(deletedExpired).toBe(1);

    const gone = await env.DB.prepare("SELECT id FROM users WHERE id = ?")
      .bind(userId)
      .first();
    expect(gone).toBeNull();
  });
});

import { env } from "cloudflare:test";
import { describe, expect, it } from "vitest";
import { createSession } from "../../src/auth/session";
import { requireAdmin } from "../../src/auth/roles";

async function createUser(role: "user" | "admin" = "user") {
  const userId = crypto.randomUUID();
  await env.DB.prepare(
    "INSERT INTO users (id, email, password_hash, role) VALUES (?, ?, ?, ?)",
  )
    .bind(userId, `${userId}@example.com`, "pbkdf2$1$AA==$AA==", role)
    .run();
  return userId;
}

function ctxFor(sessionToken: string) {
  return {
    req: {
      raw: new Request("https://services.vectora.company/admin/users", {
        headers: { Authorization: `Bearer ${sessionToken}` },
      }),
    },
    env,
  };
}

describe("requireAdmin", () => {
  it("resolves the user id for an admin, and rejects a non-admin", async () => {
    const adminId = await createUser("admin");
    const adminSession = await createSession(env.DB, adminId);
    expect(await requireAdmin(ctxFor(adminSession.token))).toBe(adminId);

    const userId = await createUser("user");
    const userSession = await createSession(env.DB, userId);
    expect(await requireAdmin(ctxFor(userSession.token))).toBeNull();
  });

  it("rejects a missing or invalid session token", async () => {
    expect(
      await requireAdmin({
        req: {
          raw: new Request("https://services.vectora.company/admin/users"),
        },
        env,
      }),
    ).toBeNull();
    expect(await requireAdmin(ctxFor("not-a-real-token"))).toBeNull();
  });
});

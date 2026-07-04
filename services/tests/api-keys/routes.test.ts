import { env } from "cloudflare:test";
import { describe, expect, it } from "vitest";
import { apiKeys } from "../../src/api-keys/routes";
import { createSession } from "../../src/auth/session";

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

describe("api-keys", () => {
  it("creates, lists, and revokes a key scoped to its owner; rejects invalid scopes", async () => {
    const { token } = await makeUserWithSession();
    const auth = {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    };

    const invalidScopes = await apiKeys.request(
      "/",
      {
        method: "POST",
        headers: auth,
        body: JSON.stringify({ name: "ci", scopes: ["superadmin"] }),
      },
      env,
    );
    expect(invalidScopes.status).toBe(400);

    const created = await apiKeys.request(
      "/",
      {
        method: "POST",
        headers: auth,
        body: JSON.stringify({ name: "ci", scopes: ["read"] }),
      },
      env,
    );
    expect(created.status).toBe(200);
    const { secret } = await created.json<{ secret: string }>();
    expect(secret).toMatch(/^vk_/);

    const list = await apiKeys.request("/", { headers: auth }, env);
    const keys =
      await list.json<Array<{ id: string; name: string; scopes: string[] }>>();
    expect(keys).toHaveLength(1);
    expect(keys[0]!.scopes).toEqual(["read"]);

    const revoke = await apiKeys.request(
      `/${keys[0]!.id}/revoke`,
      { method: "POST", headers: auth },
      env,
    );
    expect(revoke.status).toBe(200);

    const revokeAgain = await apiKeys.request(
      `/${keys[0]!.id}/revoke`,
      { method: "POST", headers: auth },
      env,
    );
    expect(revokeAgain.status).toBe(404);
  });

  it("rejects unauthenticated requests", async () => {
    const res = await apiKeys.request("/", {}, env);
    expect(res.status).toBe(401);
  });

  it("rejects an empty name and reports a conflict for a duplicate name", async () => {
    const { token } = await makeUserWithSession();
    const auth = {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    };

    const emptyName = await apiKeys.request(
      "/",
      {
        method: "POST",
        headers: auth,
        body: JSON.stringify({ name: "", scopes: ["read"] }),
      },
      env,
    );
    expect(emptyName.status).toBe(400);

    const first = await apiKeys.request(
      "/",
      {
        method: "POST",
        headers: auth,
        body: JSON.stringify({ name: "dup", scopes: ["read"] }),
      },
      env,
    );
    expect(first.status).toBe(200);

    const duplicate = await apiKeys.request(
      "/",
      {
        method: "POST",
        headers: auth,
        body: JSON.stringify({ name: "dup", scopes: ["read"] }),
      },
      env,
    );
    expect(duplicate.status).toBe(409);
    expect(await duplicate.json()).toEqual({ error: "name_taken" });
  });
});

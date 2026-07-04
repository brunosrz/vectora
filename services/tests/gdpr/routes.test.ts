import { env } from "cloudflare:test";
import { describe, expect, it, vi, afterEach } from "vitest";
import {
  gdpr,
  enqueueExpiredUserDeletions,
  hardDeleteOneUser,
} from "../../src/gdpr/routes";
import { auth } from "../../src/auth/routes";
import { createSession } from "../../src/auth/session";

afterEach(() => {
  vi.unstubAllGlobals();
});

async function makeExpiredUser(sub?: {
  provider: "stripe" | "asaas";
  customer_id?: string;
  provider_id?: string;
}) {
  const userId = crypto.randomUUID();
  await env.DB.prepare(
    "INSERT INTO users (id, email, password_hash, soft_delete_at) VALUES (?, ?, ?, ?)",
  )
    .bind(
      userId,
      `${userId}@example.com`,
      "pbkdf2$1$AA==$AA==",
      new Date(Date.now() - 31 * 24 * 60 * 60 * 1000).toISOString(),
    )
    .run();
  if (sub) {
    await env.DB.prepare(
      "INSERT INTO subscriptions (id, user_id, tier, status, currency, provider, provider_id, customer_id) VALUES (?, ?, 'pro', 'canceled', 'USD', ?, ?, ?)",
    )
      .bind(
        crypto.randomUUID(),
        userId,
        sub.provider,
        sub.provider_id ?? null,
        sub.customer_id ?? null,
      )
      .run();
  }
  return userId;
}

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

describe("POST /gdpr/delete + enqueueExpiredUserDeletions", () => {
  it("soft-deletes now and only enqueues a deletion job once the retention window has passed", async () => {
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

    const meAfterDelete = await auth.request(
      "/me",
      { headers: { Authorization: `Bearer ${token}` } },
      env,
    );
    expect(meAfterDelete.status).toBe(401);

    const sendSpy = vi.spyOn(env.JOBS_QUEUE, "send");

    const enqueuedNow = await enqueueExpiredUserDeletions(env);
    expect(enqueuedNow).toBe(0);
    expect(sendSpy).not.toHaveBeenCalled();

    await env.DB.prepare("UPDATE users SET soft_delete_at = ? WHERE id = ?")
      .bind(
        new Date(Date.now() - 31 * 24 * 60 * 60 * 1000).toISOString(),
        userId,
      )
      .run();

    const enqueuedExpired = await enqueueExpiredUserDeletions(env);
    expect(enqueuedExpired).toBe(1);
    expect(sendSpy).toHaveBeenCalledExactlyOnceWith({
      type: "gdpr_delete_user",
      userId,
    });

    // enqueueExpiredUserDeletions só enfileira — o usuário continua no D1
    // até o consumer da fila chamar hardDeleteOneUser.
    const stillThere = await env.DB.prepare("SELECT id FROM users WHERE id = ?")
      .bind(userId)
      .first();
    expect(stillThere).not.toBeNull();

    // Fecha o ciclo (e evita vazar esse usuário expirado pros próximos
    // testes do describe): é o que o consumer real faria ao processar o
    // job enfileirado acima.
    await hardDeleteOneUser(env, userId);
  });

  it("enqueues one job per expired user when there are several", async () => {
    const first = await makeExpiredUser();
    const second = await makeExpiredUser();

    const sendSpy = vi.spyOn(env.JOBS_QUEUE, "send");
    const enqueued = await enqueueExpiredUserDeletions(env);

    expect(enqueued).toBe(2);
    expect(sendSpy).toHaveBeenCalledWith({
      type: "gdpr_delete_user",
      userId: first,
    });
    expect(sendSpy).toHaveBeenCalledWith({
      type: "gdpr_delete_user",
      userId: second,
    });
  });
});

describe("hardDeleteOneUser", () => {
  it("cancels the stripe subscription before deleting a stripe user", async () => {
    const userId = await makeExpiredUser({
      provider: "stripe",
      provider_id: "sub_1",
    });
    const fetchMock = vi.fn(
      async () => new Response(JSON.stringify({ id: "sub_1", canceled: true })),
    );
    vi.stubGlobal("fetch", fetchMock);

    await hardDeleteOneUser(env, userId);
    expect(fetchMock).toHaveBeenCalled();

    const gone = await env.DB.prepare("SELECT id FROM users WHERE id = ?")
      .bind(userId)
      .first();
    expect(gone).toBeNull();
  });

  it("deletes the asaas customer before deleting an asaas user", async () => {
    const userId = await makeExpiredUser({
      provider: "asaas",
      customer_id: "cus_br_1",
    });
    const fetchMock = vi.fn(async () => new Response(JSON.stringify({})));
    vi.stubGlobal("fetch", fetchMock);

    await hardDeleteOneUser(env, userId);
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/customers/cus_br_1"),
      expect.objectContaining({ method: "DELETE" }),
    );

    const gone = await env.DB.prepare("SELECT id FROM users WHERE id = ?")
      .bind(userId)
      .first();
    expect(gone).toBeNull();
  });

  it("still deletes the user even if the provider cancellation call fails", async () => {
    const userId = await makeExpiredUser({
      provider: "stripe",
      provider_id: "sub_2",
    });
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new Error("network down");
      }),
    );

    await hardDeleteOneUser(env, userId);

    const gone = await env.DB.prepare("SELECT id FROM users WHERE id = ?")
      .bind(userId)
      .first();
    expect(gone).toBeNull();
  });

  it("throws instead of swallowing the error when the delete itself fails — the queue decides retry", async () => {
    const userId = await makeExpiredUser();
    const originalPrepare = env.DB.prepare.bind(env.DB);
    const prepareSpy = vi
      .spyOn(env.DB, "prepare")
      .mockImplementation((query: string) => {
        if (query.startsWith("DELETE FROM users")) {
          throw new Error("boom");
        }
        return originalPrepare(query);
      });

    await expect(hardDeleteOneUser(env, userId)).rejects.toThrow("boom");

    prepareSpy.mockRestore();
  });
});

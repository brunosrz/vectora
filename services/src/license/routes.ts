/**
 * license/ — porta company/supabase/functions/{validate-license,agent-login,
 * rotate-token}/index.ts + a parte de token de company/src/server/fns/token.ts.
 *
 * /validate e /agent-login são públicos (o desktop/CLI ainda não tem sessão
 * web — validate-license nem tem conceito de "usuário logado", é só o
 * VECTORA_TOKEN; agent-login troca email+senha por esse token).
 */
import { Hono } from "hono";
import type { Env } from "../relay/types";
import { requireUserId } from "../auth/routes";
import { verifyPassword } from "../auth/password";
import { sha256Hex } from "../auth/session";

export const license = new Hono<{ Bindings: Env }>();

function randomHex(bytes: number): string {
  const arr = crypto.getRandomValues(new Uint8Array(bytes));
  return Array.from(arr)
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

interface SubStatusRow {
  status: string;
  tier: string;
  trial_ends_at: string | null;
  current_period_end: string | null;
}

license.post("/validate", async (c) => {
  const body = await c.req.json<{ token?: string; version?: string }>();
  const version = body.version ?? "unknown";
  if (!body.token)
    return c.json({ valid: false, error: "token_required" }, 400);

  const tokenHash = await sha256Hex(body.token);
  const tokenRow = await c.env.DB.prepare(
    "SELECT user_id FROM tokens WHERE token_hash = ?",
  )
    .bind(tokenHash)
    .first<{ user_id: string }>();

  if (!tokenRow) {
    return c.json({ valid: false, reason: "not_found" });
  }
  const uid = tokenRow.user_id;

  const sub = await c.env.DB.prepare(
    "SELECT status, tier, trial_ends_at, current_period_end FROM subscriptions WHERE user_id = ?",
  )
    .bind(uid)
    .first<SubStatusRow>();

  let result: "valid" | "invalid" | "expired" | "not_found" = "invalid";
  let status: "active" | "trial" | "expired" | "revoked" | "unknown" =
    "unknown";
  let expiresAt = "";
  let daysRemaining = 0;

  if (sub) {
    const now = new Date();
    if (sub.status === "active") {
      result = "valid";
      status = "active";
      expiresAt = sub.current_period_end ?? "";
    } else if (sub.status === "trialing" && sub.trial_ends_at) {
      const trialEnd = new Date(sub.trial_ends_at);
      result = trialEnd > now ? "valid" : "expired";
      status = result === "valid" ? "trial" : "expired";
      expiresAt = sub.trial_ends_at;
    } else if (sub.status === "past_due") {
      result = "valid"; // grace period
      status = "active";
      expiresAt = sub.current_period_end ?? "";
    } else {
      result = "expired";
      status = "expired";
    }
    if (expiresAt) {
      daysRemaining = Math.max(
        0,
        Math.ceil((new Date(expiresAt).getTime() - now.getTime()) / 86_400_000),
      );
    }
  }

  const ip = c.req.header("cf-connecting-ip") ?? "";
  await c.env.DB.prepare(
    "INSERT INTO license_checks (id, user_id, vectora_version, result, ip) VALUES (?, ?, ?, ?, ?)",
  )
    .bind(crypto.randomUUID(), uid, version, result, ip)
    .run();

  return c.json({
    valid: result === "valid",
    reason: result,
    tier: sub?.tier ?? null,
    status,
    days_remaining: daysRemaining,
    expires_at: expiresAt,
  });
});

license.post("/agent-login", async (c) => {
  const body = await c.req.json<{ email?: string; password?: string }>();
  if (!body.email || !body.password) {
    return c.json({ error: "email_and_password_required" }, 400);
  }

  const user = await c.env.DB.prepare(
    "SELECT id, password_hash FROM users WHERE email = ?",
  )
    .bind(body.email.toLowerCase())
    .first<{ id: string; password_hash: string }>();
  if (!user) return c.json({ error: "invalid_credentials" }, 401);

  const valid = await verifyPassword(body.password, user.password_hash);
  if (!valid) return c.json({ error: "invalid_credentials" }, 401);

  const tokenRow = await c.env.DB.prepare(
    "SELECT token, token_hash FROM tokens WHERE user_id = ?",
  )
    .bind(user.id)
    .first<{ token: string | null; token_hash: string }>();
  if (!tokenRow) return c.json({ error: "token_not_found" }, 404);

  let raw: string;
  if (tokenRow.token) {
    // Nunca revelado — entrega o raw existente e anula (show-once).
    raw = tokenRow.token;
    await c.env.DB.prepare("UPDATE tokens SET token = NULL WHERE user_id = ?")
      .bind(user.id)
      .run();
  } else {
    // Já revelado — rotaciona (invalida o token antigo).
    raw = randomHex(32);
    const newHash = await sha256Hex(raw);
    await c.env.DB.prepare(
      "UPDATE tokens SET token = NULL, token_hash = ? WHERE user_id = ?",
    )
      .bind(newHash, user.id)
      .run();
  }

  const sub = await c.env.DB.prepare(
    "SELECT tier, status FROM subscriptions WHERE user_id = ?",
  )
    .bind(user.id)
    .first<{ tier: string; status: string }>();

  return c.json({
    token: raw,
    tier: sub?.tier ?? null,
    status: sub?.status ?? null,
  });
});

license.post("/rotate", async (c) => {
  const userId = await requireUserId(c);
  if (!userId) return c.json({ error: "unauthorized" }, 401);

  const current = await c.env.DB.prepare(
    "SELECT id FROM tokens WHERE user_id = ?",
  )
    .bind(userId)
    .first();
  if (!current) return c.json({ error: "token_not_found" }, 404);

  const raw = randomHex(32);
  const hash = await sha256Hex(raw);
  await c.env.DB.prepare(
    "UPDATE tokens SET token = ?, token_hash = ? WHERE user_id = ?",
  )
    .bind(raw, hash, userId)
    .run();

  return c.json({ token: raw });
});

license.get("/token-status", async (c) => {
  const userId = await requireUserId(c);
  if (!userId) return c.json({ error: "unauthorized" }, 401);

  const row = await c.env.DB.prepare(
    "SELECT token FROM tokens WHERE user_id = ?",
  )
    .bind(userId)
    .first<{ token: string | null }>();
  return c.json({ revealed: row?.token === null });
});

license.post("/token/reveal", async (c) => {
  const userId = await requireUserId(c);
  if (!userId) return c.json({ error: "unauthorized" }, 401);

  const row = await c.env.DB.prepare(
    "SELECT token FROM tokens WHERE user_id = ?",
  )
    .bind(userId)
    .first<{ token: string | null }>();
  if (!row || row.token === null)
    return c.json({ revealed: true, token: null });

  await c.env.DB.prepare("UPDATE tokens SET token = NULL WHERE user_id = ?")
    .bind(userId)
    .run();

  return c.json({ revealed: false, token: row.token });
});

license.get("/history", async (c) => {
  const userId = await requireUserId(c);
  if (!userId) return c.json({ error: "unauthorized" }, 401);

  const { results } = await c.env.DB.prepare(
    "SELECT * FROM license_checks WHERE user_id = ? ORDER BY checked_at DESC LIMIT 20",
  )
    .bind(userId)
    .all();
  return c.json(results);
});

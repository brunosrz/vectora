/**
 * auth/ — substitui o Supabase Auth da company (signup/login/sessão).
 *
 * Porta company/src/server/fns/auth.ts + a parte de auth do trigger
 * handle_new_user (company/supabase/migrations/20250629000000_free_pro_tier.sql)
 * — cria user + token de licença + subscription free no signup, igual o
 * trigger fazia.
 *
 * Sessão é o token opaco de src/auth/session.ts, não JWT — ver o comentário
 * lá pra entender por quê (company é a única consumidora, server-to-server).
 */
import { Hono } from "hono";
import type { Env } from "../gateway/types";
import { hashPassword, verifyPassword } from "./password";
import {
  createSession,
  resolveSession,
  revokeSession,
  bearerToken,
  sha256Hex,
} from "./session";
import { verifyTurnstile } from "../lib/turnstile";
import { verifyEmailHtml, magicLinkHtml } from "../lib/email";
import { enqueueEmail } from "../lib/queue";

export const auth = new Hono<{ Bindings: Env }>();

const VERIFY_TTL_MS = 24 * 60 * 60 * 1000; // 24h — verificação de email
const MAGIC_LINK_TTL_MS = 15 * 60 * 1000; // 15min

interface UserRow {
  id: string;
  email: string;
  password_hash: string;
  full_name: string;
  country: string;
  language: string;
  email_verified: number;
  role: string;
}

function randomHex(bytes: number): string {
  const arr = crypto.getRandomValues(new Uint8Array(bytes));
  return Array.from(arr)
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

/** Aplica um presente 'pending' com esse email no signup (podia ter sido
 * concedido antes mesmo da conta existir — ver admin/routes.ts). */
async function applyPendingGift(
  db: D1Database,
  userId: string,
  email: string,
): Promise<void> {
  const gift = await db
    .prepare(
      "SELECT id, duration_months FROM gifts WHERE email = ? AND status = 'pending'",
    )
    .bind(email)
    .first<{ id: string; duration_months: number | null }>();
  if (!gift) return;

  const currentPeriodEnd = gift.duration_months
    ? (() => {
        const d = new Date();
        d.setMonth(d.getMonth() + gift.duration_months!);
        return d.toISOString();
      })()
    : null;

  await db
    .prepare(
      "UPDATE subscriptions SET tier = 'pro', status = 'active', provider = 'gift', current_period_end = ?, updated_at = datetime('now') WHERE user_id = ?",
    )
    .bind(currentPeriodEnd, userId)
    .run();

  await db
    .prepare(
      "UPDATE gifts SET status = 'claimed', claimed_user_id = ?, claimed_at = datetime('now') WHERE id = ?",
    )
    .bind(userId, gift.id)
    .run();
}

async function createEmailVerification(
  db: D1Database,
  userId: string,
  purpose: "verify_email" | "magic_link",
  ttlMs: number,
): Promise<string> {
  const token = randomHex(32);
  const tokenHash = await sha256Hex(token);
  const expiresAt = new Date(Date.now() + ttlMs).toISOString();
  await db
    .prepare(
      "INSERT INTO email_verifications (id, user_id, token_hash, purpose, expires_at) VALUES (?, ?, ?, ?, ?)",
    )
    .bind(crypto.randomUUID(), userId, tokenHash, purpose, expiresAt)
    .run();
  return token;
}

auth.post("/signup", async (c) => {
  const body = await c.req.json<{
    name?: string;
    email?: string;
    password?: string;
    country?: "BR" | "INTL";
    turnstileToken?: string;
  }>();

  if (!body.name || body.name.length < 2) {
    return c.json({ error: "name_required" }, 400);
  }
  if (!body.email || !body.email.includes("@")) {
    return c.json({ error: "invalid_email" }, 400);
  }
  if (!body.password || body.password.length < 8) {
    return c.json({ error: "password_too_short" }, 400);
  }
  if (!body.turnstileToken) {
    return c.json({ error: "turnstile_required" }, 400);
  }

  const turnstile = await verifyTurnstile(
    body.turnstileToken,
    c.env.TURNSTILE_SECRET_KEY,
    c.req.header("cf-connecting-ip"),
  );
  if (!turnstile.success) return c.json({ error: "turnstile_failed" }, 400);

  const email = body.email.toLowerCase();
  const existing = await c.env.DB.prepare(
    "SELECT id FROM users WHERE email = ?",
  )
    .bind(email)
    .first();
  if (existing) return c.json({ error: "email_taken" }, 409);

  const country: "BR" | "INTL" = body.country === "BR" ? "BR" : "INTL";
  const userId = crypto.randomUUID();
  const passwordHash = await hashPassword(body.password);

  await c.env.DB.prepare(
    "INSERT INTO users (id, email, password_hash, full_name, country) VALUES (?, ?, ?, ?, ?)",
  )
    .bind(userId, email, passwordHash, body.name, country)
    .run();

  // Token de licença (VECTORA_TOKEN) — recuperável a qualquer momento pelo
  // dashboard (GET /license/token/reveal), identifica a conta e o plano
  // ativo (free ou pro) pro app local. Todo signup recebe um, mesmo Free.
  const rawToken = randomHex(32);
  const tokenHash = await sha256Hex(rawToken);
  await c.env.DB.prepare(
    "INSERT INTO tokens (id, user_id, token, token_hash) VALUES (?, ?, ?, ?)",
  )
    .bind(crypto.randomUUID(), userId, rawToken, tokenHash)
    .run();

  await c.env.DB.prepare(
    "INSERT INTO subscriptions (id, user_id, tier, status, currency, trial_ends_at) VALUES (?, ?, 'free', 'active', ?, NULL)",
  )
    .bind(crypto.randomUUID(), userId, country === "BR" ? "BRL" : "USD")
    .run();

  await applyPendingGift(c.env.DB, userId, email);

  const verifyToken = await createEmailVerification(
    c.env.DB,
    userId,
    "verify_email",
    VERIFY_TTL_MS,
  );
  const verifyUrl = `${c.env.APP_URL}/auth/verify?token=${verifyToken}`;
  await enqueueEmail(c.env, {
    to: email,
    subject: "Confirme seu email — Vectora",
    html: verifyEmailHtml(body.name, verifyUrl),
  });

  return c.json({ needsConfirmation: true, email });
});

auth.post("/verify", async (c) => {
  const body = await c.req.json<{ token?: string }>();
  if (!body.token) return c.json({ error: "token_required" }, 400);

  const tokenHash = await sha256Hex(body.token);
  const row = await c.env.DB.prepare(
    "SELECT id, user_id, purpose, expires_at, used_at FROM email_verifications WHERE token_hash = ?",
  )
    .bind(tokenHash)
    .first<{
      id: string;
      user_id: string;
      purpose: string;
      expires_at: string;
      used_at: string | null;
    }>();

  if (!row) return c.json({ error: "invalid_token" }, 404);
  if (row.used_at) return c.json({ error: "token_already_used" }, 410);
  if (new Date(row.expires_at).getTime() < Date.now()) {
    return c.json({ error: "token_expired" }, 410);
  }

  await c.env.DB.prepare(
    "UPDATE email_verifications SET used_at = ? WHERE id = ?",
  )
    .bind(new Date().toISOString(), row.id)
    .run();

  if (row.purpose === "verify_email") {
    await c.env.DB.prepare("UPDATE users SET email_verified = 1 WHERE id = ?")
      .bind(row.user_id)
      .run();
  }

  const session = await createSession(c.env.DB, row.user_id);
  return c.json({
    session_token: session.token,
    expires_at: session.expiresAt,
    redirect: "/dashboard?welcome=true",
  });
});

auth.post("/login", async (c) => {
  const body = await c.req.json<{ email?: string; password?: string }>();
  if (!body.email || !body.password) {
    return c.json({ error: "email_and_password_required" }, 400);
  }

  const user = await c.env.DB.prepare(
    "SELECT id, password_hash, email_verified FROM users WHERE email = ?",
  )
    .bind(body.email.toLowerCase())
    .first<{ id: string; password_hash: string; email_verified: number }>();

  if (!user) return c.json({ error: "invalid_credentials" }, 401);

  const valid = await verifyPassword(body.password, user.password_hash);
  if (!valid) return c.json({ error: "invalid_credentials" }, 401);

  if (!user.email_verified) {
    return c.json({ error: "email_not_verified" }, 403);
  }

  const session = await createSession(c.env.DB, user.id);
  return c.json({
    session_token: session.token,
    expires_at: session.expiresAt,
  });
});

auth.post("/logout", async (c) => {
  const token = bearerToken(c.req.raw);
  if (token) await revokeSession(c.env.DB, token);
  return c.json({ ok: true });
});

auth.post("/magic-link", async (c) => {
  const body = await c.req.json<{ email?: string }>();
  if (!body.email) return c.json({ error: "email_required" }, 400);

  const user = await c.env.DB.prepare("SELECT id FROM users WHERE email = ?")
    .bind(body.email.toLowerCase())
    .first<{ id: string }>();

  // Não revela se o email existe ou não (evita user enumeration) — sempre
  // 200; só envia de verdade se encontrar.
  if (user) {
    const token = await createEmailVerification(
      c.env.DB,
      user.id,
      "magic_link",
      MAGIC_LINK_TTL_MS,
    );
    const loginUrl = `${c.env.APP_URL}/auth/verify?token=${token}`;
    await enqueueEmail(c.env, {
      to: body.email,
      subject: "Seu link de acesso — Vectora",
      html: magicLinkHtml(loginUrl),
    });
  }

  return c.json({ ok: true });
});

auth.get("/me", async (c) => {
  const userId = await resolveSession(c.env.DB, bearerToken(c.req.raw));
  if (!userId) return c.json({ error: "unauthorized" }, 401);

  const user = await c.env.DB.prepare(
    "SELECT id, email, full_name, country, language, email_verified, role FROM users WHERE id = ?",
  )
    .bind(userId)
    .first<UserRow>();
  if (!user) return c.json({ error: "not_found" }, 404);

  return c.json({
    id: user.id,
    email: user.email,
    full_name: user.full_name,
    country: user.country,
    language: user.language,
    email_verified: Boolean(user.email_verified),
    role: user.role,
  });
});

/** Helper reutilizado pelos outros módulos de rota (billing/license/gdpr/...). */
export async function requireUserId(c: {
  req: { raw: Request };
  env: Env;
}): Promise<string | null> {
  return resolveSession(c.env.DB, bearerToken(c.req.raw));
}

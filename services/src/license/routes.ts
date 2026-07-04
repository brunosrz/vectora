/**
 * license/ — porta company/supabase/functions/{validate-license,agent-login,
 * rotate-token,create-portal}/index.ts + a parte de token de
 * company/src/server/fns/token.ts.
 *
 * /validate, /agent-login e /portal são autenticados por VECTORA_TOKEN, não
 * por sessão web — o desktop/CLI Python nunca tem cookie de sessão, só o
 * token de licença. /portal duplica a lógica de billing/routes.ts (troca só
 * a autenticação: sessão → token) porque o backend Python chama esta rota
 * diretamente com o VECTORA_TOKEN salvo em config.toml.
 */
import { Hono } from "hono";
import type { Env } from "../relay/types";
import { requireUserId } from "../auth/routes";
import { verifyPassword } from "../auth/password";
import { sha256Hex } from "../auth/session";
import { stripeClient } from "../billing/routes";

export const license = new Hono<{ Bindings: Env }>();

async function userIdForToken(env: Env, token: string): Promise<string | null> {
  const tokenHash = await sha256Hex(token);
  const row = await env.DB.prepare(
    "SELECT user_id FROM tokens WHERE token_hash = ?",
  )
    .bind(tokenHash)
    .first<{ user_id: string }>();
  return row?.user_id ?? null;
}

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

  // Token é recuperável (mesmo modelo de /token/reveal): devolve o mesmo raw
  // sempre, nunca anula. Antes disso rotacionava a cada 2º login — o que
  // invalidava silenciosamente o token já configurado numa instalação
  // anterior sempre que o usuário conectasse uma segunda máquina.
  let raw: string;
  if (tokenRow.token) {
    raw = tokenRow.token;
  } else {
    // Linha legada de antes da mudança pra token recuperável (token já
    // tinha sido zerado por um /agent-login ou /token/reveal antigo) —
    // usuário já provou identidade via senha, então é seguro bootstrapar
    // um token novo aqui em vez de mandar ele pro dashboard rotacionar.
    raw = randomHex(32);
    const newHash = await sha256Hex(raw);
    await c.env.DB.prepare(
      "UPDATE tokens SET token = ?, token_hash = ? WHERE user_id = ?",
    )
      .bind(raw, newHash, user.id)
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

interface PortalSubRow {
  currency: string;
  customer_id: string | null;
}

license.post("/portal", async (c) => {
  const body = await c.req.json<{ token?: string }>();
  if (!body.token) return c.json({ error: "token_required" }, 400);

  const userId = await userIdForToken(c.env, body.token);
  if (!userId) return c.json({ error: "invalid_token" }, 401);

  const sub = await c.env.DB.prepare(
    "SELECT currency, customer_id FROM subscriptions WHERE user_id = ?",
  )
    .bind(userId)
    .first<PortalSubRow>();
  if (!sub?.customer_id) return c.json({ error: "no_customer_found" }, 404);

  const appUrl = c.env.APP_URL;

  if (sub.currency === "BRL") {
    const asaasBase = c.env.ASAAS_API_URL || "https://api.asaas.com/v3";
    const customerRes = await fetch(
      `${asaasBase}/customers/${sub.customer_id}`,
      { headers: { access_token: c.env.ASAAS_API_KEY } },
    );
    const customer = await customerRes.json<{ billingInfoUrl?: string }>();
    return c.json({
      url: customer.billingInfoUrl ?? `${appUrl}/dashboard/billing`,
    });
  }

  const stripe = stripeClient(c.env);
  const portal = await stripe.billingPortal.sessions.create({
    customer: sub.customer_id,
    return_url: `${appUrl}/dashboard/billing`,
  });
  return c.json({ url: portal.url });
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

// O VECTORA_TOKEN é recuperável: `token` (plaintext) fica gravado na tabela
// indefinidamente, não só até o primeiro reveal. É o mesmo modelo de uma
// license key que o usuário pode voltar a ver em "minha conta" a qualquer
// momento — perder acesso ao próprio token de licença é pior UX do que o
// ganho marginal de segurança de um show-once. Rotacionar continua sendo a
// forma de invalidar o token atual (ex.: suspeita de vazamento).
license.get("/token-status", async (c) => {
  const userId = await requireUserId(c);
  if (!userId) return c.json({ error: "unauthorized" }, 401);

  const row = await c.env.DB.prepare(
    "SELECT token FROM tokens WHERE user_id = ?",
  )
    .bind(userId)
    .first<{ token: string | null }>();
  return c.json({ available: row?.token != null });
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
    return c.json({ error: "token_not_found" }, 404);

  return c.json({ token: row.token });
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

/**
 * gdpr/ — porta company/src/server/fns/gdpr.ts (export/delete) +
 * company/supabase/functions/cron-hard-delete/index.ts (agora Cloudflare
 * Cron Trigger nativo, ver scheduled() em src/index.ts, não pg_cron/HTTP).
 *
 * Export usa o bucket R2 já existente (`R2`, vectora-r2) com prefixo
 * `exports/` — evita provisionar um bucket novo só pra isso; são poucos
 * bytes de JSON por usuário, não briga de espaço com os instaladores.
 */
import { Hono } from "hono";
import Stripe from "stripe";
import type { Env } from "../relay/types";
import { requireUserId } from "../auth/routes";
import { bearerToken, revokeSession } from "../auth/session";
import { accountDeletedHtml } from "../lib/email";
import { enqueueEmail, enqueueJob } from "../lib/queue";

export const gdpr = new Hono<{ Bindings: Env }>();

gdpr.post("/export", async (c) => {
  const userId = await requireUserId(c);
  if (!userId) return c.json({ error: "unauthorized" }, 401);

  const [user, subscriptions, licenseChecks, apiKeys] = await Promise.all([
    c.env.DB.prepare("SELECT * FROM users WHERE id = ?").bind(userId).first(),
    c.env.DB.prepare("SELECT * FROM subscriptions WHERE user_id = ?")
      .bind(userId)
      .all(),
    c.env.DB.prepare("SELECT * FROM license_checks WHERE user_id = ?")
      .bind(userId)
      .all(),
    c.env.DB.prepare(
      "SELECT id, name, scopes, created_at, last_used_at FROM api_keys WHERE user_id = ?",
    )
      .bind(userId)
      .all(),
  ]);

  const payload = JSON.stringify(
    {
      profile: user,
      subscriptions: subscriptions.results,
      license_checks: licenseChecks.results,
      api_keys: apiKeys.results,
      exported_at: new Date().toISOString(),
    },
    null,
    2,
  );

  const key = `exports/${userId}-${Date.now()}.json`;
  await c.env.R2.put(key, payload, {
    httpMetadata: { contentType: "application/json" },
  });

  // R2 binding não gera URL assinada nativamente como o Supabase Storage —
  // servida via /gdpr/export/* (rota abaixo, wildcard porque `key` já tem
  // uma barra em "exports/"), efêmera o bastante (link pessoal, não
  // indexado, sem listagem pública do bucket).
  return c.json({ url: `${c.env.APP_URL}/api/gdpr/export/${key}` });
});

gdpr.get("/export/*", async (c) => {
  const userId = await requireUserId(c);
  if (!userId) return c.json({ error: "unauthorized" }, 401);

  const key = c.req.path.replace(/^.*\/export\//, "");
  if (!key.startsWith(`exports/${userId}-`)) {
    // Só o dono pode baixar o próprio export.
    return c.json({ error: "forbidden" }, 403);
  }

  const obj = await c.env.R2.get(key);
  if (!obj) return c.json({ error: "not_found" }, 404);

  return new Response(obj.body, {
    headers: { "Content-Type": "application/json" },
  });
});

gdpr.post("/delete", async (c) => {
  const userId = await requireUserId(c);
  if (!userId) return c.json({ error: "unauthorized" }, 401);

  const user = await c.env.DB.prepare(
    "SELECT email, full_name FROM users WHERE id = ?",
  )
    .bind(userId)
    .first<{ email: string; full_name: string }>();
  if (!user) return c.json({ error: "not_found" }, 404);

  const deletionDate = new Date(
    Date.now() + 30 * 24 * 60 * 60 * 1000,
  ).toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "long",
    year: "numeric",
  });

  await enqueueEmail(c.env, {
    to: user.email,
    subject: "Conta Vectora agendada para exclusão",
    html: accountDeletedHtml(user.full_name || user.email, deletionDate),
  });

  await c.env.DB.prepare("UPDATE users SET soft_delete_at = ? WHERE id = ?")
    .bind(new Date().toISOString(), userId)
    .run();

  const token = bearerToken(c.req.raw);
  if (token) await revokeSession(c.env.DB, token);

  return c.json({ ok: true });
});

/**
 * Deleta um único usuário expirado (cancela billing externo + apaga do D1).
 * Lança em vez de só logar — quem decide retry agora é o consumer da fila
 * `vectora-jobs` (job `gdpr_delete_user`), não este loop.
 */
export async function hardDeleteOneUser(env: Env, uid: string): Promise<void> {
  const sub = await env.DB.prepare(
    "SELECT provider, customer_id, provider_id FROM subscriptions WHERE user_id = ?",
  )
    .bind(uid)
    .first<{
      provider: string | null;
      customer_id: string | null;
      provider_id: string | null;
    }>();

  if (sub?.provider === "stripe" && sub.provider_id) {
    const stripe = new Stripe(env.STRIPE_SECRET_KEY, {
      apiVersion: "2024-12-18.acacia" as never,
      httpClient: Stripe.createFetchHttpClient(),
    });
    await stripe.subscriptions.cancel(sub.provider_id).catch(() => null);
  }
  if (sub?.provider === "asaas" && sub.customer_id) {
    const asaasBase = env.ASAAS_API_URL || "https://api.asaas.com/v3";
    await fetch(`${asaasBase}/customers/${sub.customer_id}`, {
      method: "DELETE",
      headers: { access_token: env.ASAAS_API_KEY },
    }).catch(() => null);
  }

  // ON DELETE CASCADE cuida de sessions/tokens/subscriptions/etc.
  await env.DB.prepare("DELETE FROM users WHERE id = ?").bind(uid).run();
}

/**
 * Chamado pelo Cron Trigger em src/index.ts (scheduled()) — enfileira 1 job
 * `gdpr_delete_user` por usuário expirado em vez de deletar tudo numa
 * invocação de cron só (cada usuário ganha retry independente na fila).
 */
export async function enqueueExpiredUserDeletions(env: Env): Promise<number> {
  const cutoff = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString();
  const { results } = await env.DB.prepare(
    "SELECT id FROM users WHERE soft_delete_at IS NOT NULL AND soft_delete_at < ?",
  )
    .bind(cutoff)
    .all<{ id: string }>();

  for (const { id: userId } of results) {
    await enqueueJob(env, { type: "gdpr_delete_user", userId });
  }
  return results.length;
}

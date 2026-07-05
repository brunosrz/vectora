/**
 * admin/ — painel do criador do Vectora: lista de usuários, cupons
 * (desconto/free_lifetime) e presentes de licença. Toda rota exige
 * `role = 'admin'` via requireAdmin — não há UI pública, é whitelist
 * implícita (usuário comum recebe 403, rota não é escondida por segurança
 * por obscuridade).
 */
import { Hono } from "hono";
import type { Env } from "../relay/types";
import { requireAdmin } from "../auth/roles";
import { grantSubscription } from "../billing/routes";
import { giftReceivedHtml } from "../lib/email";
import { enqueueEmail } from "../lib/queue";

export const admin = new Hono<{ Bindings: Env }>();

admin.get("/users", async (c) => {
  const adminId = await requireAdmin(c);
  if (!adminId) return c.json({ error: "forbidden" }, 403);

  const limit = Math.min(Number(c.req.query("limit") ?? "50"), 200);
  const offset = Number(c.req.query("offset") ?? "0");

  const { results } = await c.env.DB.prepare(
    `SELECT u.id, u.email, u.full_name, u.created_at,
            s.tier, s.status, s.current_period_end
     FROM users u
     LEFT JOIN subscriptions s ON s.user_id = u.id
     ORDER BY u.created_at DESC
     LIMIT ? OFFSET ?`,
  )
    .bind(limit, offset)
    .all();

  return c.json({ users: results });
});

interface CouponListRow {
  id: string;
  code: string;
  kind: string;
  grant_plan_id: string | null;
  charge_plan_id: string | null;
  max_redemptions: number | null;
  times_redeemed: number;
  active: number;
  expires_at: string | null;
  created_at: string;
}

admin.get("/coupons", async (c) => {
  const adminId = await requireAdmin(c);
  if (!adminId) return c.json({ error: "forbidden" }, 403);

  const { results } = await c.env.DB.prepare(
    "SELECT * FROM coupons ORDER BY created_at DESC",
  ).all<CouponListRow>();

  return c.json({ coupons: results });
});

admin.post("/coupons", async (c) => {
  const adminId = await requireAdmin(c);
  if (!adminId) return c.json({ error: "forbidden" }, 403);

  const body = await c.req.json<{
    code?: string;
    kind?: "discount" | "free_lifetime";
    grant_plan_id?: string;
    charge_plan_id?: string;
    max_redemptions?: number;
    expires_at?: string;
  }>();

  if (!body.code || body.code.trim().length < 3) {
    return c.json({ error: "invalid_code" }, 400);
  }
  if (body.kind !== "discount" && body.kind !== "free_lifetime") {
    return c.json({ error: "invalid_kind" }, 400);
  }
  if (
    body.kind === "discount" &&
    (!body.grant_plan_id || !body.charge_plan_id)
  ) {
    return c.json({ error: "discount_requires_plans" }, 400);
  }

  const code = body.code.trim().toUpperCase();

  try {
    await c.env.DB.prepare(
      `INSERT INTO coupons
         (id, code, kind, grant_plan_id, charge_plan_id, max_redemptions, created_by, expires_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
    )
      .bind(
        crypto.randomUUID(),
        code,
        body.kind,
        body.kind === "discount" ? (body.grant_plan_id ?? null) : null,
        body.kind === "discount" ? (body.charge_plan_id ?? null) : null,
        body.max_redemptions ?? null,
        adminId,
        body.expires_at ?? null,
      )
      .run();
  } catch {
    return c.json({ error: "code_taken" }, 409);
  }

  return c.json({ ok: true, code });
});

admin.post("/coupons/:id/deactivate", async (c) => {
  const adminId = await requireAdmin(c);
  if (!adminId) return c.json({ error: "forbidden" }, 403);

  const id = c.req.param("id");
  const result = await c.env.DB.prepare(
    "UPDATE coupons SET active = 0 WHERE id = ?",
  )
    .bind(id)
    .run();

  if (result.meta.changes === 0) return c.json({ error: "not_found" }, 404);
  return c.json({ ok: true });
});

admin.get("/gifts", async (c) => {
  const adminId = await requireAdmin(c);
  if (!adminId) return c.json({ error: "forbidden" }, 403);

  const { results } = await c.env.DB.prepare(
    `SELECT g.id, g.email, g.duration_months, g.status, g.created_at, g.claimed_at,
            u.email as granted_by_email
     FROM gifts g
     JOIN users u ON u.id = g.granted_by
     ORDER BY g.created_at DESC`,
  ).all();

  return c.json({ gifts: results });
});

admin.post("/gifts", async (c) => {
  const adminId = await requireAdmin(c);
  if (!adminId) return c.json({ error: "forbidden" }, 403);

  const body = await c.req.json<{ email?: string; duration_months?: number }>();
  if (!body.email || !body.email.includes("@")) {
    return c.json({ error: "invalid_email" }, 400);
  }
  const email = body.email.toLowerCase();
  const durationMonths = body.duration_months ?? null;

  const granter = await c.env.DB.prepare(
    "SELECT full_name FROM users WHERE id = ?",
  )
    .bind(adminId)
    .first<{ full_name: string }>();

  const existingUser = await c.env.DB.prepare(
    "SELECT id FROM users WHERE email = ?",
  )
    .bind(email)
    .first<{ id: string }>();

  const giftId = crypto.randomUUID();
  await c.env.DB.prepare(
    `INSERT INTO gifts (id, email, granted_by, duration_months, status, claimed_user_id, claimed_at)
     VALUES (?, ?, ?, ?, ?, ?, ?)`,
  )
    .bind(
      giftId,
      email,
      adminId,
      durationMonths,
      existingUser ? "claimed" : "pending",
      existingUser?.id ?? null,
      existingUser ? new Date().toISOString() : null,
    )
    .run();

  if (existingUser) {
    const currentPeriodEnd = durationMonths
      ? (() => {
          const d = new Date();
          d.setMonth(d.getMonth() + durationMonths);
          return d.toISOString();
        })()
      : null;
    await grantSubscription(c.env.DB, existingUser.id, {
      provider: "gift",
      currentPeriodEnd,
    });
  }

  const durationLabel = durationMonths
    ? `${durationMonths} meses`
    : "Vitalício";
  const ctaUrl = existingUser
    ? `${c.env.APP_URL}/dashboard`
    : `${c.env.APP_URL}/auth/signup?email=${encodeURIComponent(email)}`;
  await enqueueEmail(c.env, {
    to: email,
    subject: "Você recebeu o Vectora Pro de presente!",
    html: giftReceivedHtml(
      granter?.full_name ?? "Vectora",
      durationLabel,
      ctaUrl,
    ),
  });

  return c.json({ ok: true, gift_id: giftId, claimed: Boolean(existingUser) });
});

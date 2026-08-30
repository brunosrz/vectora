/**
 * billing/ — porta company/supabase/functions/{create-checkout,create-portal,
 * webhooks}/index.ts quase 1:1, só troca o client Supabase (admin.from(...))
 * por D1 (c.env.DB.prepare(...)).
 *
 * Só existe checkout de Pro — Free não passa por aqui (sem conta seria
 * incoerente, mas mesmo com conta, Free nunca cobra nada).
 */
import { Hono } from "hono";
import Stripe from "stripe";
import type { Env } from "../gateway/types";
import { requireUserId } from "../auth/routes";
import { invoicePaidHtml, invoiceFailedHtml } from "../lib/email";
import { enqueueEmail } from "../lib/queue";
import { getPlan, ensureStripePrice, type Plan } from "./plans";

export const billing = new Hono<{ Bindings: Env }>();

/** Expira presentes/cupons com prazo fixo vencido — vitalícios
 * (current_period_end NULL) nunca entram aqui. Rodado 1x/dia (ver
 * scheduled() em index.ts, mesmo cron do GDPR hard-delete). */
export async function expireGiftSubscriptions(db: D1Database): Promise<number> {
  // current_period_end é gravado como ISO8601 (toISOString(), com "T"/"Z") —
  // comparar contra datetime('now') do SQLite ("YYYY-MM-DD HH:MM:SS", sem
  // "T"/"Z") quebra a ordenação lexicográfica na hora certa do dia. Bindar
  // um ISO8601 calculado em JS mantém os dois lados no mesmo formato.
  const result = await db
    .prepare(
      `UPDATE subscriptions SET status = 'expired', tier = 'free'
       WHERE provider = 'gift' AND current_period_end IS NOT NULL
         AND current_period_end < ? AND status = 'active'`,
    )
    .bind(new Date().toISOString())
    .run();
  return result.meta.changes ?? 0;
}

billing.get("/subscription", async (c) => {
  const userId = await requireUserId(c);
  if (!userId) return c.json({ error: "unauthorized" }, 401);

  const sub = await c.env.DB.prepare(
    "SELECT * FROM subscriptions WHERE user_id = ?",
  )
    .bind(userId)
    .first();
  if (!sub) return c.json({ error: "not_found" }, 404);
  return c.json(sub);
});

export function stripeClient(env: Env): Stripe {
  return new Stripe(env.STRIPE_SECRET_KEY, {
    apiVersion: "2024-12-18.acacia" as never,
    httpClient: Stripe.createFetchHttpClient(),
  });
}

interface SubRow {
  currency: string;
  customer_id: string | null;
}

interface CouponRow {
  id: string;
  code: string;
  kind: "discount" | "free_lifetime";
  grant_plan_id: string | null;
  charge_plan_id: string | null;
  max_redemptions: number | null;
  times_redeemed: number;
  active: number;
  expires_at: string | null;
}

async function resolveCoupon(
  db: D1Database,
  code: string,
  userId: string,
): Promise<CouponRow | "invalid" | "already_redeemed"> {
  const coupon = await db
    .prepare("SELECT * FROM coupons WHERE code = ? AND active = 1")
    .bind(code.toUpperCase())
    .first<CouponRow>();
  if (!coupon) return "invalid";
  if (coupon.expires_at && new Date(coupon.expires_at).getTime() < Date.now()) {
    return "invalid";
  }
  if (
    coupon.max_redemptions !== null &&
    coupon.times_redeemed >= coupon.max_redemptions
  ) {
    return "invalid";
  }

  const already = await db
    .prepare(
      "SELECT id FROM coupon_redemptions WHERE coupon_id = ? AND user_id = ?",
    )
    .bind(coupon.id, userId)
    .first();
  if (already) return "already_redeemed";

  return coupon;
}

async function redeemCoupon(
  db: D1Database,
  coupon: CouponRow,
  userId: string,
): Promise<void> {
  await db
    .prepare(
      "INSERT INTO coupon_redemptions (id, coupon_id, user_id) VALUES (?, ?, ?)",
    )
    .bind(crypto.randomUUID(), coupon.id, userId)
    .run();

  const nextRedeemed = coupon.times_redeemed + 1;
  const exhausted =
    coupon.max_redemptions !== null && nextRedeemed >= coupon.max_redemptions;
  await db
    .prepare(
      exhausted
        ? "UPDATE coupons SET times_redeemed = ?, active = 0 WHERE id = ?"
        : "UPDATE coupons SET times_redeemed = ? WHERE id = ?",
    )
    .bind(nextRedeemed, coupon.id)
    .run();
}

/** Aplica a redenção (audit + contador) a partir do id do cupom — usado pelos
 * webhooks assíncronos (Stripe/Asaas), onde só o `coupon_id` sobrevive no
 * metadata/externalReference, não a row completa já resolvida no checkout. */
async function redeemCouponById(
  db: D1Database,
  couponId: string,
  userId: string,
): Promise<void> {
  const coupon = await db
    .prepare("SELECT * FROM coupons WHERE id = ?")
    .bind(couponId)
    .first<CouponRow>();
  if (!coupon) return;

  const already = await db
    .prepare(
      "SELECT id FROM coupon_redemptions WHERE coupon_id = ? AND user_id = ?",
    )
    .bind(couponId, userId)
    .first();
  if (already) return;

  await redeemCoupon(db, coupon, userId);
}

export async function grantSubscription(
  db: D1Database,
  userId: string,
  params: {
    provider: "gift" | "asaas" | "stripe";
    currentPeriodEnd: string | null;
  },
): Promise<void> {
  await db
    .prepare(
      "UPDATE subscriptions SET tier = 'pro', status = 'active', provider = ?, current_period_end = ?, updated_at = datetime('now') WHERE user_id = ?",
    )
    .bind(params.provider, params.currentPeriodEnd, userId)
    .run();
}

billing.post("/checkout", async (c) => {
  const userId = await requireUserId(c);
  if (!userId) return c.json({ error: "unauthorized" }, 401);

  const user = await c.env.DB.prepare("SELECT email FROM users WHERE id = ?")
    .bind(userId)
    .first<{ email: string }>();
  if (!user) return c.json({ error: "not_found" }, 404);

  const body = await c.req.json<{ plan_id?: string; coupon_code?: string }>();
  if (!body.plan_id) return c.json({ error: "plan_id_required" }, 400);

  const requestedPlan = await getPlan(c.env.DB, body.plan_id);
  if (!requestedPlan) return c.json({ error: "invalid_plan" }, 400);

  let coupon: CouponRow | null = null;
  if (body.coupon_code) {
    const resolved = await resolveCoupon(c.env.DB, body.coupon_code, userId);
    if (resolved === "invalid") return c.json({ error: "invalid_coupon" }, 400);
    if (resolved === "already_redeemed") {
      return c.json({ error: "coupon_already_redeemed" }, 409);
    }
    coupon = resolved;
  }

  if (coupon?.kind === "free_lifetime") {
    await grantSubscription(c.env.DB, userId, {
      provider: "gift",
      currentPeriodEnd: null,
    });
    await redeemCoupon(c.env.DB, coupon, userId);
    return c.json({ redeemed: true });
  }

  // Cupom 'discount': cobra charge_plan_id mas concede grant_plan_id.
  const chargePlan =
    coupon?.kind === "discount"
      ? ((await getPlan(c.env.DB, coupon.charge_plan_id!)) as Plan)
      : requestedPlan;
  const grantPlanId =
    coupon?.kind === "discount" ? coupon.grant_plan_id! : requestedPlan.id;

  const sub = await c.env.DB.prepare(
    "SELECT currency, customer_id FROM subscriptions WHERE user_id = ?",
  )
    .bind(userId)
    .first<SubRow>();

  const appUrl = c.env.APP_URL;

  if (sub?.currency === "BRL") {
    // Asaas (BR)
    const asaasBase = c.env.ASAAS_API_URL || "https://api.asaas.com/v3";
    const amount = chargePlan.price_brl_cents / 100;

    const paymentRes = await fetch(`${asaasBase}/payments`, {
      method: "POST",
      headers: {
        access_token: c.env.ASAAS_API_KEY,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        customer: user.email,
        billingType: "UNDEFINED",
        value: amount,
        dueDate: new Date(Date.now() + 86_400_000).toISOString().split("T")[0],
        description: `Vectora Pro — ${grantPlanId}`,
        externalReference: `${userId}:${grantPlanId}:${coupon?.id ?? ""}`,
      }),
    });
    const payment = await paymentRes.json<{
      invoiceUrl?: string;
      bankSlipUrl?: string;
    }>();
    const checkoutUrl =
      payment.invoiceUrl ??
      payment.bankSlipUrl ??
      `${appUrl}/dashboard/billing`;
    return c.json({ url: checkoutUrl });
  }

  // Stripe (INTL)
  const stripe = stripeClient(c.env);
  let customerId = sub?.customer_id ?? null;
  if (!customerId) {
    const customer = await stripe.customers.create({
      email: user.email,
      metadata: { user_id: userId },
    });
    customerId = customer.id;
    await c.env.DB.prepare(
      "UPDATE subscriptions SET customer_id = ? WHERE user_id = ?",
    )
      .bind(customerId, userId)
      .run();
  }

  const priceId = await ensureStripePrice(
    stripe,
    c.env.DB,
    chargePlan,
    c.env.STRIPE_PRICE_PRO_USD,
  );

  const session = await stripe.checkout.sessions.create({
    customer: customerId,
    mode: "subscription",
    line_items: [{ price: priceId, quantity: 1 }],
    success_url: `${appUrl}/dashboard/billing?success=1`,
    cancel_url: `${appUrl}/dashboard/billing`,
    metadata: {
      user_id: userId,
      plan: grantPlanId,
      coupon_id: coupon?.id ?? "",
    },
  });

  return c.json({ url: session.url });
});

billing.post("/portal", async (c) => {
  const userId = await requireUserId(c);
  if (!userId) return c.json({ error: "unauthorized" }, 401);

  const sub = await c.env.DB.prepare(
    "SELECT currency, customer_id FROM subscriptions WHERE user_id = ?",
  )
    .bind(userId)
    .first<SubRow>();
  if (!sub?.customer_id) return c.json({ error: "no_customer_found" }, 404);

  const appUrl = c.env.APP_URL;

  if (sub.currency === "BRL") {
    const asaasBase = c.env.ASAAS_API_URL || "https://api.asaas.com/v3";
    const customerRes = await fetch(
      `${asaasBase}/customers/${sub.customer_id}`,
      {
        headers: { access_token: c.env.ASAAS_API_KEY },
      },
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

async function getUserEmail(
  db: D1Database,
  userId: string,
): Promise<string | null> {
  const row = await db
    .prepare("SELECT email FROM users WHERE id = ?")
    .bind(userId)
    .first<{ email: string }>();
  return row?.email ?? null;
}

async function insertPaymentEvent(
  db: D1Database,
  params: {
    userId: string | null;
    provider: "stripe" | "asaas";
    eventType: string;
    payload: unknown;
  },
): Promise<void> {
  await db
    .prepare(
      "INSERT INTO payment_events (id, user_id, provider, event_type, payload, processed_at) VALUES (?, ?, ?, ?, ?, ?)",
    )
    .bind(
      crypto.randomUUID(),
      params.userId,
      params.provider,
      params.eventType,
      JSON.stringify(params.payload),
      new Date().toISOString(),
    )
    .run();
}

billing.post("/webhooks", async (c) => {
  const provider = c.req.query("provider");
  if (provider === "stripe") return handleStripeWebhook(c);
  if (provider === "asaas") return handleAsaasWebhook(c);
  return c.json({ error: "unknown_provider" }, 400);
});

async function handleStripeWebhook(c: {
  req: { raw: Request; header: (n: string) => string | undefined };
  env: Env;
  json: (b: unknown, s?: number) => Response;
}): Promise<Response> {
  const stripe = stripeClient(c.env);
  const sig = c.req.header("stripe-signature");
  const body = await c.req.raw.text();

  let event: Stripe.Event;
  try {
    event = await stripe.webhooks.constructEventAsync(
      body,
      sig!,
      c.env.STRIPE_WEBHOOK_SECRET,
    );
  } catch {
    return c.json({ error: "signature_failed" }, 400);
  }

  const uid = (event.data.object as { metadata?: { user_id?: string } })
    ?.metadata?.user_id;

  await insertPaymentEvent(c.env.DB, {
    userId: uid ?? null,
    provider: "stripe",
    eventType: event.type,
    payload: event.data.object,
  });

  if (event.type === "invoice.paid" && uid) {
    const inv = event.data.object as Stripe.Invoice;
    const subscriptionId = inv.parent?.subscription_details?.subscription;
    const subId =
      typeof subscriptionId === "string" ? subscriptionId : subscriptionId?.id;
    const sub = await stripe.subscriptions.retrieve(subId as string);
    const grantPlanId =
      (sub.metadata?.plan as string | undefined) ??
      (sub.items.data[0]?.price?.metadata?.plan as string | undefined) ??
      "1m";
    const couponId = sub.metadata?.coupon_id as string | undefined;
    const periodEndSeconds = sub.items.data[0]?.current_period_end ?? 0;
    const periodEndIso = new Date(periodEndSeconds * 1000).toISOString();
    const periodEnd = new Date(periodEndSeconds * 1000).toLocaleDateString(
      "pt-BR",
      { day: "2-digit", month: "long", year: "numeric" },
    );

    await c.env.DB.prepare(
      "UPDATE subscriptions SET status = 'active', tier = 'pro', provider = 'stripe', provider_id = ?, current_period_end = ? WHERE user_id = ?",
    )
      .bind(sub.id, periodEndIso, uid)
      .run();

    if (couponId) await redeemCouponById(c.env.DB, couponId, uid);

    const email = await getUserEmail(c.env.DB, uid);
    if (email) {
      const amount = (inv.amount_paid / 100).toLocaleString("en-US", {
        style: "currency",
        currency: inv.currency.toUpperCase(),
      });
      await enqueueEmail(c.env, {
        to: email,
        subject: "Pagamento confirmado — Vectora",
        html: invoicePaidHtml(email, amount, grantPlanId, periodEnd),
      });
    }
  }

  if (event.type === "invoice.payment_failed" && uid) {
    const inv = event.data.object as Stripe.Invoice;
    await c.env.DB.prepare(
      "UPDATE subscriptions SET status = 'past_due' WHERE user_id = ?",
    )
      .bind(uid)
      .run();

    const email = await getUserEmail(c.env.DB, uid);
    if (email) {
      const amount = (inv.amount_due / 100).toLocaleString("en-US", {
        style: "currency",
        currency: inv.currency.toUpperCase(),
      });
      await enqueueEmail(c.env, {
        to: email,
        subject: "Falha no pagamento — Vectora",
        html: invoiceFailedHtml(email, amount),
      });
    }
  }

  if (event.type === "customer.subscription.deleted" && uid) {
    // tier volta pra "free" — sem isso o gate require_pro() do backend Python
    // continuaria liberando pra sempre (ele checa tier, não status).
    await c.env.DB.prepare(
      "UPDATE subscriptions SET status = 'canceled', tier = 'free', canceled_at = ? WHERE user_id = ?",
    )
      .bind(new Date().toISOString(), uid)
      .run();
  }

  return c.json({ ok: true });
}

async function handleAsaasWebhook(c: {
  req: { raw: Request; header: (n: string) => string | undefined };
  env: Env;
  json: (b: unknown, s?: number) => Response;
}): Promise<Response> {
  // asaas-access-token: token fixo configurado no painel Asaas
  // (Menu do usuário > Integrações > Mecanismos de segurança), enviado em
  // TODA notificação — sem essa checagem, qualquer request forjado com um
  // user_id válido em externalReference concede/cancela Pro à vontade.
  // Falha fechado: secret ausente/vazio nunca deve "casar" com header
  // ausente (os dois undefined comparariam iguais e liberariam geral).
  if (
    !c.env.ASAAS_WEBHOOK_SECRET ||
    c.req.header("asaas-access-token") !== c.env.ASAAS_WEBHOOK_SECRET
  ) {
    return c.json({ error: "invalid_webhook_token" }, 401);
  }

  const body = await c.req.raw.json<{
    event?: string;
    payment?: {
      externalReference?: string;
      id?: string;
      value?: number;
    };
  }>();
  const externalRef = body.payment?.externalReference ?? "";
  const [uid, grantPlanId, couponId] = externalRef.split(":");
  const event = body.event ?? "";

  await insertPaymentEvent(c.env.DB, {
    userId: uid || null,
    provider: "asaas",
    eventType: event,
    payload: body,
  });

  if ((event === "PAYMENT_RECEIVED" || event === "PAYMENT_CONFIRMED") && uid) {
    // Só existe checkout de Pro — pagamento confirmado sempre vira tier "pro".
    const plan = await getPlan(c.env.DB, grantPlanId ?? "");
    const periodEndDate = new Date();
    periodEndDate.setMonth(periodEndDate.getMonth() + (plan?.months ?? 1));

    await c.env.DB.prepare(
      "UPDATE subscriptions SET status = 'active', tier = 'pro', provider = 'asaas', provider_id = ?, current_period_end = ? WHERE user_id = ?",
    )
      .bind(body.payment?.id ?? null, periodEndDate.toISOString(), uid)
      .run();

    if (couponId) await redeemCouponById(c.env.DB, couponId, uid);

    const email = await getUserEmail(c.env.DB, uid);
    if (email) {
      const amount = `R$${((body.payment?.value ?? 0) as number).toFixed(2).replace(".", ",")}`;
      const periodEnd = periodEndDate.toLocaleDateString("pt-BR", {
        day: "2-digit",
        month: "long",
        year: "numeric",
      });
      await enqueueEmail(c.env, {
        to: email,
        subject: "Pagamento confirmado — Vectora",
        html: invoicePaidHtml(email, amount, grantPlanId ?? "Pro", periodEnd),
      });
    }
  }

  if (event === "PAYMENT_OVERDUE" && uid) {
    await c.env.DB.prepare(
      "UPDATE subscriptions SET status = 'past_due' WHERE user_id = ?",
    )
      .bind(uid)
      .run();

    const email = await getUserEmail(c.env.DB, uid);
    if (email) {
      const amount = `R$${((body.payment?.value ?? 0) as number).toFixed(2).replace(".", ",")}`;
      await enqueueEmail(c.env, {
        to: email,
        subject: "Falha no pagamento — Vectora",
        html: invoiceFailedHtml(email, amount),
      });
    }
  }

  if ((event === "PAYMENT_DELETED" || event === "PAYMENT_REFUNDED") && uid) {
    await c.env.DB.prepare(
      "UPDATE subscriptions SET status = 'canceled', tier = 'free' WHERE user_id = ?",
    )
      .bind(uid)
      .run();
  }

  return c.json({ ok: true });
}

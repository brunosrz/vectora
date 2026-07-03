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
import type { Env } from "../relay/types";
import { requireUserId } from "../auth/routes";
import { sendEmail, invoicePaidHtml, invoiceFailedHtml } from "../lib/email";

export const billing = new Hono<{ Bindings: Env }>();

function stripeClient(env: Env): Stripe {
  return new Stripe(env.STRIPE_SECRET_KEY, {
    apiVersion: "2024-12-18.acacia" as never,
    httpClient: Stripe.createFetchHttpClient(),
  });
}

interface SubRow {
  currency: string;
  customer_id: string | null;
}

billing.post("/checkout", async (c) => {
  const userId = await requireUserId(c);
  if (!userId) return c.json({ error: "unauthorized" }, 401);

  const user = await c.env.DB.prepare("SELECT email FROM users WHERE id = ?")
    .bind(userId)
    .first<{ email: string }>();
  if (!user) return c.json({ error: "not_found" }, 404);

  const sub = await c.env.DB.prepare(
    "SELECT currency, customer_id FROM subscriptions WHERE user_id = ?",
  )
    .bind(userId)
    .first<SubRow>();

  const appUrl = c.env.APP_URL;

  if (sub?.currency === "BRL") {
    // Asaas (BR)
    const asaasBase = c.env.ASAAS_API_URL || "https://api.asaas.com/v3";
    const amount = 24.0;

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
        description: "Vectora Pro — 1 mês",
        externalReference: `${userId}:pro`,
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

  const session = await stripe.checkout.sessions.create({
    customer: customerId,
    mode: "subscription",
    line_items: [{ price: c.env.STRIPE_PRICE_PRO_USD, quantity: 1 }],
    success_url: `${appUrl}/dashboard/billing?success=1`,
    cancel_url: `${appUrl}/dashboard/billing`,
    metadata: { user_id: userId, plan: "pro" },
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
    const plan =
      (sub.metadata?.plan as string | undefined) ??
      (sub.items.data[0]?.price?.metadata?.plan as string | undefined) ??
      "pro";
    const periodEndSeconds = sub.items.data[0]?.current_period_end ?? 0;
    const periodEndIso = new Date(periodEndSeconds * 1000).toISOString();
    const periodEnd = new Date(periodEndSeconds * 1000).toLocaleDateString(
      "pt-BR",
      { day: "2-digit", month: "long", year: "numeric" },
    );

    await c.env.DB.prepare(
      "UPDATE subscriptions SET status = 'active', tier = ?, provider = 'stripe', provider_id = ?, current_period_end = ? WHERE user_id = ?",
    )
      .bind(plan, sub.id, periodEndIso, uid)
      .run();

    const email = await getUserEmail(c.env.DB, uid);
    if (email) {
      const amount = (inv.amount_paid / 100).toLocaleString("en-US", {
        style: "currency",
        currency: inv.currency.toUpperCase(),
      });
      await sendEmail(c.env.RESEND_API_KEY, {
        to: email,
        subject: "Pagamento confirmado — Vectora",
        html: invoicePaidHtml(email, amount, plan, periodEnd),
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
      await sendEmail(c.env.RESEND_API_KEY, {
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
  req: { raw: Request };
  env: Env;
  json: (b: unknown, s?: number) => Response;
}): Promise<Response> {
  const body = await c.req.raw.json<{
    event?: string;
    payment?: {
      externalReference?: string;
      id?: string;
      value?: number;
    };
  }>();
  const externalRef = body.payment?.externalReference ?? "";
  const [uid, plan] = externalRef.split(":");
  const event = body.event ?? "";

  await insertPaymentEvent(c.env.DB, {
    userId: uid || null,
    provider: "asaas",
    eventType: event,
    payload: body,
  });

  if ((event === "PAYMENT_RECEIVED" || event === "PAYMENT_CONFIRMED") && uid) {
    // Só existe checkout de Pro — pagamento confirmado sempre vira tier "pro".
    await c.env.DB.prepare(
      "UPDATE subscriptions SET status = 'active', tier = 'pro', provider = 'asaas', provider_id = ? WHERE user_id = ?",
    )
      .bind(body.payment?.id ?? null, uid)
      .run();

    const email = await getUserEmail(c.env.DB, uid);
    if (email) {
      const amount = `R$${((body.payment?.value ?? 0) as number).toFixed(2).replace(".", ",")}`;
      const periodEnd = new Date(
        Date.now() + 30 * 24 * 60 * 60 * 1000,
      ).toLocaleDateString("pt-BR", {
        day: "2-digit",
        month: "long",
        year: "numeric",
      });
      await sendEmail(c.env.RESEND_API_KEY, {
        to: email,
        subject: "Pagamento confirmado — Vectora",
        html: invoicePaidHtml(email, amount, plan ?? "Pro", periodEnd),
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
      await sendEmail(c.env.RESEND_API_KEY, {
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

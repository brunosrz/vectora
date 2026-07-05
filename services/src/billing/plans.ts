import type Stripe from "stripe";

export interface Plan {
  id: string;
  months: number;
  price_usd_cents: number;
  price_brl_cents: number;
  stripe_price_id: string | null;
  active: number;
}

export async function getPlan(
  db: D1Database,
  planId: string,
): Promise<Plan | null> {
  const plan = await db
    .prepare("SELECT * FROM plans WHERE id = ? AND active = 1")
    .bind(planId)
    .first<Plan>();
  return plan ?? null;
}

/**
 * Cria o Stripe Price do plano sob demanda (1x por plano) e persiste o id —
 * evita ter que cadastrar preço na mão no dashboard da Stripe pra cada nova
 * duração. O produto reaproveitado é o mesmo do plano mensal já existente
 * (`STRIPE_PRICE_PRO_USD`), só a recorrência (`interval_count`) muda.
 */
export async function ensureStripePrice(
  stripe: Stripe,
  db: D1Database,
  plan: Plan,
  baseStripePriceId: string,
): Promise<string> {
  if (plan.stripe_price_id) return plan.stripe_price_id;

  const basePrice = await stripe.prices.retrieve(baseStripePriceId);
  const productId =
    typeof basePrice.product === "string"
      ? basePrice.product
      : basePrice.product.id;

  const price = await stripe.prices.create({
    unit_amount: plan.price_usd_cents,
    currency: "usd",
    recurring: { interval: "month", interval_count: plan.months },
    product: productId,
  });

  await db
    .prepare("UPDATE plans SET stripe_price_id = ? WHERE id = ?")
    .bind(price.id, plan.id)
    .run();

  return price.id;
}

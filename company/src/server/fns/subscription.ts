import { createServerFn } from "@tanstack/react-start";
import { z } from "zod";
import { servicesFetch } from "#/lib/services/client";

// Espelha services/migrations/0003_rbac_billing.sql (plans seedados) —
// preço exibido aqui é cosmético; o backend é a fonte de verdade do valor
// cobrado de fato no checkout.
export const PLANS = [
  { id: "1m", months: 1, priceUsd: 9, priceBrl: 24 },
  { id: "3m", months: 3, priceUsd: 27, priceBrl: 72 },
  { id: "6m", months: 6, priceUsd: 51, priceBrl: 136 },
  { id: "12m", months: 12, priceUsd: 96, priceBrl: 256 },
  { id: "36m", months: 36, priceUsd: 259, priceBrl: 691 },
] as const;

export type PlanId = (typeof PLANS)[number]["id"];

export interface Subscription {
  id: string;
  user_id: string;
  tier: "free" | "pro";
  status: string;
  currency: "BRL" | "USD";
  provider: "asaas" | "stripe" | null;
  provider_id: string | null;
  customer_id: string | null;
  started_at: string;
  current_period_end: string | null;
  canceled_at: string | null;
}

export interface LicenseCheck {
  id: string;
  user_id: string;
  vectora_version: string;
  result: "valid" | "invalid" | "expired" | "not_found";
  ip: string | null;
  checked_at: string;
}

export const getSubscription = createServerFn({ method: "GET" }).handler(
  async (): Promise<Subscription | null> => {
    try {
      return await servicesFetch<Subscription>("/billing/subscription");
    } catch (err) {
      if (err instanceof Error && err.message === "not_found") return null;
      throw err;
    }
  },
);

const CheckoutSchema = z.object({
  planId: z.string().min(1),
  couponCode: z.string().min(1).optional(),
});

export const createCheckout = createServerFn({ method: "POST" })
  .validator(CheckoutSchema)
  .handler(async ({ data }) => {
    return servicesFetch<{ url: string } | { redeemed: true }>(
      "/billing/checkout",
      {
        method: "POST",
        body: JSON.stringify({
          plan_id: data.planId,
          coupon_code: data.couponCode,
        }),
      },
    );
  });

export const createPortal = createServerFn({ method: "POST" }).handler(
  async () => {
    return servicesFetch<{ url: string }>("/billing/portal", {
      method: "POST",
    });
  },
);

export const getLicenseHistory = createServerFn({ method: "GET" }).handler(
  async () => {
    return servicesFetch<LicenseCheck[]>("/license/history");
  },
);

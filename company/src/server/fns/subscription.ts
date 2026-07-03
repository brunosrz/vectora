import { createServerFn } from "@tanstack/react-start";
import { servicesFetch } from "#/lib/services/client";

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
  trial_ends_at: string | null;
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

export const createCheckout = createServerFn({ method: "POST" }).handler(
  async () => {
    return servicesFetch<{ url: string }>("/billing/checkout", {
      method: "POST",
    });
  },
);

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

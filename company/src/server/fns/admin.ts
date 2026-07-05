import { createServerFn } from "@tanstack/react-start";
import { z } from "zod";
import { servicesFetch } from "#/lib/services/client";

export interface AdminUserRow {
  id: string;
  email: string;
  full_name: string;
  created_at: string;
  tier: "free" | "pro" | null;
  status: string | null;
  current_period_end: string | null;
}

export interface AdminCouponRow {
  id: string;
  code: string;
  kind: "discount" | "free_lifetime";
  grant_plan_id: string | null;
  charge_plan_id: string | null;
  max_redemptions: number | null;
  times_redeemed: number;
  active: number;
  expires_at: string | null;
  created_at: string;
}

export interface AdminGiftRow {
  id: string;
  email: string;
  duration_months: number | null;
  status: "pending" | "claimed";
  created_at: string;
  claimed_at: string | null;
  granted_by_email: string;
}

export const listUsers = createServerFn({ method: "GET" })
  .validator(
    z.object({ limit: z.number().optional(), offset: z.number().optional() }),
  )
  .handler(async ({ data }) => {
    const params = new URLSearchParams();
    if (data.limit) params.set("limit", String(data.limit));
    if (data.offset) params.set("offset", String(data.offset));
    const qs = params.toString();
    return servicesFetch<{ users: AdminUserRow[] }>(
      `/admin/users${qs ? `?${qs}` : ""}`,
    );
  });

export const listCoupons = createServerFn({ method: "GET" }).handler(
  async () => {
    return servicesFetch<{ coupons: AdminCouponRow[] }>("/admin/coupons");
  },
);

const CreateCouponSchema = z.object({
  code: z.string().min(3),
  kind: z.enum(["discount", "free_lifetime"]),
  grant_plan_id: z.string().optional(),
  charge_plan_id: z.string().optional(),
  max_redemptions: z.number().int().positive().optional(),
  expires_at: z.string().optional(),
});

export const createCoupon = createServerFn({ method: "POST" })
  .validator(CreateCouponSchema)
  .handler(async ({ data }) => {
    return servicesFetch<{ ok: true; code: string }>("/admin/coupons", {
      method: "POST",
      body: JSON.stringify(data),
    });
  });

export const deactivateCoupon = createServerFn({ method: "POST" })
  .validator(z.object({ id: z.string().min(1) }))
  .handler(async ({ data }) => {
    return servicesFetch<{ ok: true }>(`/admin/coupons/${data.id}/deactivate`, {
      method: "POST",
    });
  });

export const listGifts = createServerFn({ method: "GET" }).handler(async () => {
  return servicesFetch<{ gifts: AdminGiftRow[] }>("/admin/gifts");
});

const CreateGiftSchema = z.object({
  email: z.string().email(),
  duration_months: z.number().int().positive().optional(),
});

export const createGift = createServerFn({ method: "POST" })
  .validator(CreateGiftSchema)
  .handler(async ({ data }) => {
    return servicesFetch<{ ok: true; gift_id: string; claimed: boolean }>(
      "/admin/gifts",
      { method: "POST", body: JSON.stringify(data) },
    );
  });

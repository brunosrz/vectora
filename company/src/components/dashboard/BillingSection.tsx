import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { m } from "#/paraglide/messages";
import {
  getSubscription,
  createCheckout,
  createPortal,
  PLANS,
} from "#/server/fns/subscription";
import type { PlanId } from "#/server/fns/subscription";
import { toast } from "sonner";
import { ExternalLink } from "lucide-react";

const PLAN_LABELS = {
  "1m": m.billing_plan_1m,
  "3m": m.billing_plan_3m,
  "6m": m.billing_plan_6m,
  "12m": m.billing_plan_12m,
  "36m": m.billing_plan_36m,
} as const satisfies Record<PlanId, () => string>;

export default function BillingSection() {
  const queryClient = useQueryClient();
  const [planId, setPlanId] = useState<PlanId>("1m");
  const [couponCode, setCouponCode] = useState("");

  const { data: sub, isLoading } = useQuery({
    queryKey: ["subscription"],
    queryFn: () => getSubscription(),
    staleTime: 30_000,
  });

  const checkoutMutation = useMutation({
    mutationFn: () =>
      createCheckout({
        data: { planId, couponCode: couponCode.trim() || undefined },
      }),
    onSuccess: (res) => {
      if ("redeemed" in res) {
        toast.success(m.billing_coupon_redeemed());
        queryClient.invalidateQueries({ queryKey: ["subscription"] });
        return;
      }
      window.location.href = res.url;
    },
    onError: () => toast.error(m.error_generic()),
  });

  const portalMutation = useMutation({
    mutationFn: () => createPortal(),
    onSuccess: (res) => {
      window.location.href = res.url;
    },
    onError: () => toast.error(m.error_generic()),
  });

  if (isLoading) {
    return (
      <div className="h-40 max-w-xl rounded-xl bg-card/30 animate-pulse" />
    );
  }

  if (!sub) return null;

  const isBR = sub.currency === "BRL";
  const isPro = sub.tier === "pro";

  return (
    <div className="max-w-xl space-y-4">
      <div className="rounded-xl border border-border bg-card/30 p-6">
        <p className="mb-3 text-sm text-muted-foreground">
          {isBR
            ? "🇧🇷 Pagamentos via Asaas (PIX, Boleto, Cartão)"
            : "🌍 Payments via Stripe (Card)"}
        </p>

        {!isPro ? (
          <div className="flex flex-col gap-3">
            <p className="text-sm text-muted-foreground">
              {m.billing_free_desc()}
            </p>

            <label className="text-xs font-medium text-muted-foreground">
              {m.billing_plan_selector_label()}
            </label>
            <select
              value={planId}
              onChange={(e) => setPlanId(e.target.value as PlanId)}
              className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
            >
              {PLANS.map((plan) => (
                <option key={plan.id} value={plan.id}>
                  {PLAN_LABELS[plan.id]()} —{" "}
                  {isBR ? `R$${plan.priceBrl}` : `$${plan.priceUsd}`}
                </option>
              ))}
            </select>

            <label className="text-xs font-medium text-muted-foreground">
              {m.billing_coupon_label()}
            </label>
            <input
              type="text"
              value={couponCode}
              onChange={(e) => setCouponCode(e.target.value)}
              placeholder={m.billing_coupon_placeholder()}
              className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
            />

            <button
              onClick={() => checkoutMutation.mutate()}
              disabled={checkoutMutation.isPending}
              className="flex items-center justify-between rounded-xl border border-primary/50 bg-primary/5 px-4 py-3 text-sm hover:border-primary transition-all disabled:opacity-50"
            >
              <p className="font-semibold text-primary">
                {m.billing_upgrade_pro()}
              </p>
              <ExternalLink className="h-4 w-4 text-primary" />
            </button>
          </div>
        ) : (
          <button
            onClick={() => portalMutation.mutate()}
            disabled={portalMutation.isPending}
            className="w-full flex items-center justify-center gap-2 rounded-xl border border-border px-4 py-2.5 text-sm font-medium text-foreground/90 hover:border-primary hover:text-foreground disabled:opacity-50 transition-all"
          >
            <ExternalLink className="h-4 w-4" />
            {portalMutation.isPending
              ? m.form_submitting()
              : m.billing_manage()}
          </button>
        )}
      </div>

      <p className="text-xs text-muted-foreground">{m.billing_footer()}</p>
    </div>
  );
}

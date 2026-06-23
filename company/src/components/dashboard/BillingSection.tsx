import { useQuery, useMutation } from "@tanstack/react-query";
import { m } from "#/paraglide/messages";
import {
  getSubscription,
  createCheckout,
  createPortal,
} from "#/server/fns/subscription";
import { toast } from "sonner";
import { ExternalLink } from "lucide-react";

export default function BillingSection() {
  const { data: sub, isLoading } = useQuery({
    queryKey: ["subscription"],
    queryFn: () => getSubscription(),
    staleTime: 30_000,
  });

  const checkoutMutation = useMutation({
    mutationFn: (plan: "plus" | "pro") => createCheckout({ data: { plan } }),
    onSuccess: (res) => {
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
  const isActive = sub.status === "active" || sub.status === "trialing";
  const isPro = sub.tier === "pro";

  return (
    <div className="max-w-xl space-y-4">
      <div className="rounded-xl border border-border bg-card/30 p-6">
        <p className="mb-3 text-sm text-muted-foreground">
          {isBR
            ? "🇧🇷 Pagamentos via Asaas (PIX, Boleto, Cartão)"
            : "🌍 Payments via Stripe (Card)"}
        </p>

        {!isActive ? (
          <div className="flex flex-col gap-2">
            <p className="text-sm text-muted-foreground mb-3">
              {m.billing_inactive_desc()}
            </p>
            <button
              onClick={() => checkoutMutation.mutate("plus")}
              disabled={checkoutMutation.isPending}
              className="flex items-center justify-between rounded-xl border border-border px-4 py-3 text-sm hover:border-primary transition-all disabled:opacity-50"
            >
              <div>
                <p className="font-semibold text-foreground">Plus</p>
                <p className="text-muted-foreground">
                  {isBR ? "R$20/mês" : "$7/mês"}
                </p>
              </div>
              <ExternalLink className="h-4 w-4 text-muted-foreground" />
            </button>
            <button
              onClick={() => checkoutMutation.mutate("pro")}
              disabled={checkoutMutation.isPending}
              className="flex items-center justify-between rounded-xl border border-primary/50 bg-primary/5 px-4 py-3 text-sm hover:border-primary transition-all disabled:opacity-50"
            >
              <div>
                <p className="font-semibold text-primary">Pro</p>
                <p className="text-muted-foreground">
                  {isBR ? "R$55/mês" : "$20/mês"}
                </p>
              </div>
              <ExternalLink className="h-4 w-4 text-primary" />
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            {!isPro && (
              <button
                onClick={() => checkoutMutation.mutate("pro")}
                disabled={checkoutMutation.isPending}
                className="w-full rounded-xl bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-all"
              >
                {m.billing_upgrade_pro()}
              </button>
            )}
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
          </div>
        )}
      </div>

      <p className="text-xs text-muted-foreground">{m.billing_footer()}</p>
    </div>
  );
}

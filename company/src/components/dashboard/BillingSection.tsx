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
    mutationFn: () => createCheckout(),
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
            <button
              onClick={() => checkoutMutation.mutate()}
              disabled={checkoutMutation.isPending}
              className="flex items-center justify-between rounded-xl border border-primary/50 bg-primary/5 px-4 py-3 text-sm hover:border-primary transition-all disabled:opacity-50"
            >
              <div>
                <p className="font-semibold text-primary">
                  {m.billing_upgrade_pro()}
                </p>
                <p className="text-muted-foreground">
                  {isBR ? "R$24/mês" : "$9/mês"}
                </p>
              </div>
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

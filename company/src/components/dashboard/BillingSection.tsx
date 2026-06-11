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
      <div className="h-40 max-w-xl rounded-xl bg-brand-800/30 animate-pulse" />
    );
  }

  if (!sub) return null;

  const isBR = sub.currency === "BRL";
  const isActive = sub.status === "active" || sub.status === "trialing";
  const isPro = sub.tier === "pro";

  return (
    <div className="max-w-xl space-y-4">
      <div className="rounded-xl border border-brand-700 bg-brand-800/30 p-6">
        <p className="mb-3 text-sm text-slate-400">
          {isBR
            ? "🇧🇷 Pagamentos via Asaas (PIX, Boleto, Cartão)"
            : "🌍 Payments via Stripe (Card)"}
        </p>

        {!isActive ? (
          <div className="flex flex-col gap-2">
            <p className="text-sm text-slate-400 mb-3">
              {m.billing_inactive_desc()}
            </p>
            <button
              onClick={() => checkoutMutation.mutate("plus")}
              disabled={checkoutMutation.isPending}
              className="flex items-center justify-between rounded-xl border border-brand-700 px-4 py-3 text-sm hover:border-brand-500 transition-all disabled:opacity-50"
            >
              <div>
                <p className="font-semibold text-white">Plus</p>
                <p className="text-slate-400">{isBR ? "R$20/mês" : "$7/mês"}</p>
              </div>
              <ExternalLink className="h-4 w-4 text-slate-500" />
            </button>
            <button
              onClick={() => checkoutMutation.mutate("pro")}
              disabled={checkoutMutation.isPending}
              className="flex items-center justify-between rounded-xl border border-brand-500/50 bg-brand-500/5 px-4 py-3 text-sm hover:border-brand-500 transition-all disabled:opacity-50"
            >
              <div>
                <p className="font-semibold text-brand-300">Pro</p>
                <p className="text-slate-400">
                  {isBR ? "R$55/mês" : "$20/mês"}
                </p>
              </div>
              <ExternalLink className="h-4 w-4 text-brand-400" />
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            {!isPro && (
              <button
                onClick={() => checkoutMutation.mutate("pro")}
                disabled={checkoutMutation.isPending}
                className="w-full rounded-xl bg-brand-500 px-4 py-2.5 text-sm font-semibold text-white hover:bg-brand-400 disabled:opacity-50 transition-all"
              >
                {m.billing_upgrade_pro()}
              </button>
            )}
            <button
              onClick={() => portalMutation.mutate()}
              disabled={portalMutation.isPending}
              className="w-full flex items-center justify-center gap-2 rounded-xl border border-brand-700 px-4 py-2.5 text-sm font-medium text-slate-300 hover:border-brand-500 hover:text-white disabled:opacity-50 transition-all"
            >
              <ExternalLink className="h-4 w-4" />
              {portalMutation.isPending
                ? m.form_submitting()
                : m.billing_manage()}
            </button>
          </div>
        )}
      </div>

      <p className="text-xs text-slate-500">{m.billing_footer()}</p>
    </div>
  );
}

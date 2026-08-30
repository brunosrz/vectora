import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { m } from "#/paraglide/messages";
import DashboardHeading from "#/components/dashboard/DashboardHeading";
import GhBotSection from "#/components/dashboard/GhBotSection";
import { getSubscription } from "#/server/fns/subscription";

export const Route = createFileRoute("/dashboard/gh-bot")({
  component: GhBotPage,
});

function GhBotPage() {
  const { data: sub, isLoading } = useQuery({
    queryKey: ["subscription"],
    queryFn: () => getSubscription(),
    staleTime: 30_000,
  });

  const isPro = sub?.tier === "pro" && sub.status === "active";

  return (
    <div>
      <DashboardHeading title={m.nav_gh_bot()} />
      {isLoading ? (
        <div className="h-40 max-w-xl rounded-xl bg-card/30 animate-pulse" />
      ) : isPro ? (
        <GhBotSection />
      ) : (
        <div className="max-w-xl rounded-xl border border-border bg-card/30 p-6 text-center space-y-3">
          <p className="text-sm text-muted-foreground">
            {m.gh_bot_pro_required()}
          </p>
          <Link
            to="/dashboard/billing"
            className="inline-flex items-center justify-center rounded-xl border border-primary/50 bg-primary/5 px-4 py-2.5 text-sm font-semibold text-primary hover:border-primary transition-all"
          >
            {m.gh_bot_pro_cta()}
          </Link>
        </div>
      )}
    </div>
  );
}

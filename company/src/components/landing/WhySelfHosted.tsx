import { m } from "#/paraglide/messages";
import { Lock, Coins, Settings, Server } from "lucide-react";

const CARDS = [
  {
    icon: Lock,
    titleKey: "why_privacy_title",
    descKey: "why_privacy_desc",
    color: "text-primary",
    bg: "bg-primary/10",
    border: "border-border hover:border-primary",
  },
  {
    icon: Coins,
    titleKey: "why_cost_title",
    descKey: "why_cost_desc",
    color: "text-accent-green",
    bg: "bg-accent-green/10",
    border: "border-border hover:border-green-500/50",
  },
  {
    icon: Settings,
    titleKey: "why_custom_title",
    descKey: "why_custom_desc",
    color: "text-accent-purple",
    bg: "bg-purple-500/10",
    border: "border-border hover:border-purple-500/50",
  },
  {
    icon: Server,
    titleKey: "why_sovereign_title",
    descKey: "why_sovereign_desc",
    color: "text-accent-amber",
    bg: "bg-accent-amber/10",
    border: "border-border hover:border-amber-500/50",
  },
] as const;

export default function WhySelfHosted() {
  return (
    <section className="px-4 py-14 sm:px-6 sm:py-20 lg:px-8">
      <div className="mx-auto max-w-6xl">
        <div className="mb-14 text-center">
          <h2 className="mb-3 text-2xl font-semibold text-foreground sm:text-3xl">
            {m.why_heading()}
          </h2>
          <p className="mx-auto max-w-xl text-muted-foreground">
            {m.why_subtitle()}
          </p>
        </div>

        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
          {CARDS.map((card) => {
            const Icon = card.icon;
            return (
              <div
                key={card.titleKey}
                className={`rounded-xl border ${card.border} bg-card/30 p-6 transition-all duration-200`}
              >
                <div className={`mb-4 inline-flex rounded-lg p-2.5 ${card.bg}`}>
                  <Icon className={`h-5 w-5 ${card.color}`} />
                </div>
                <h3 className="mb-2 font-semibold text-foreground">
                  {m[card.titleKey]()}
                </h3>
                <p className="text-sm leading-relaxed text-muted-foreground">
                  {m[card.descKey]()}
                </p>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

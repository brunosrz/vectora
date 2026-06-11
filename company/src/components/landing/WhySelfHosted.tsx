import { m } from "#/paraglide/messages";
import { Lock, Coins, Settings, Server } from "lucide-react";

const CARDS = [
  {
    icon: Lock,
    titleKey: "why_privacy_title",
    descKey: "why_privacy_desc",
    color: "text-brand-400",
    bg: "bg-brand-500/10",
    border: "border-brand-700 hover:border-brand-500",
  },
  {
    icon: Coins,
    titleKey: "why_cost_title",
    descKey: "why_cost_desc",
    color: "text-green-400",
    bg: "bg-green-500/10",
    border: "border-brand-700 hover:border-green-500/50",
  },
  {
    icon: Settings,
    titleKey: "why_custom_title",
    descKey: "why_custom_desc",
    color: "text-purple-400",
    bg: "bg-purple-500/10",
    border: "border-brand-700 hover:border-purple-500/50",
  },
  {
    icon: Server,
    titleKey: "why_sovereign_title",
    descKey: "why_sovereign_desc",
    color: "text-amber-400",
    bg: "bg-amber-500/10",
    border: "border-brand-700 hover:border-amber-500/50",
  },
] as const;

export default function WhySelfHosted() {
  return (
    <section className="px-4 py-20 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-6xl">
        <div className="mb-14 text-center">
          <h2 className="mb-3 text-3xl font-semibold text-white sm:text-4xl">
            {m.why_heading()}
          </h2>
          <p className="mx-auto max-w-xl text-slate-400">{m.why_subtitle()}</p>
        </div>

        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
          {CARDS.map((card) => {
            const Icon = card.icon;
            return (
              <div
                key={card.titleKey}
                className={`rounded-xl border ${card.border} bg-brand-800/30 p-6 transition-all duration-200`}
              >
                <div className={`mb-4 inline-flex rounded-lg p-2.5 ${card.bg}`}>
                  <Icon className={`h-5 w-5 ${card.color}`} />
                </div>
                <h3 className="mb-2 font-semibold text-white">
                  {m[card.titleKey]()}
                </h3>
                <p className="text-sm leading-relaxed text-slate-400">
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

import { m } from "#/paraglide/messages";
import { Lock, Coins, Settings, Server } from "lucide-react";

const CARDS = [
  {
    id: "privacy",
    Icon: Lock,
    title: m.why_privacy_title,
    desc: m.why_privacy_desc,
    iconBg: "rgba(121,184,255,0.1)",
    iconColor: "var(--primary)",
  },
  {
    id: "cost",
    Icon: Coins,
    title: m.why_cost_title,
    desc: m.why_cost_desc,
    iconBg: "rgba(78,201,160,0.1)",
    iconColor: "var(--accent-green)",
  },
  {
    id: "custom",
    Icon: Settings,
    title: m.why_custom_title,
    desc: m.why_custom_desc,
    iconBg: "rgba(173,70,255,0.1)",
    iconColor: "var(--accent-purple)",
  },
  {
    id: "sovereign",
    Icon: Server,
    title: m.why_sovereign_title,
    desc: m.why_sovereign_desc,
    iconBg: "rgba(226,192,141,0.1)",
    iconColor: "var(--accent-amber)",
  },
];

export default function WhySelfHosted() {
  return (
    <section className="bg-background/50 py-[23px]">
      <div className="mx-auto flex max-w-[1024px] flex-col items-center gap-8 px-4 sm:px-6 lg:px-0">
        {/* Heading */}
        <div className="flex flex-col items-center gap-3">
          <h2 className="text-center text-[28px] font-semibold leading-[36px] text-foreground">
            {m.why_heading()}
          </h2>
          <p className="text-center text-base leading-6 text-muted-foreground">
            {m.why_subtitle()}
          </p>
        </div>

        {/* Grid 2×2 */}
        <div className="grid w-full grid-cols-1 gap-5 sm:grid-cols-2">
          {CARDS.map((card) => {
            const { Icon } = card;
            return (
              <div
                key={card.id}
                className="flex flex-col gap-2 rounded-2xl border border-border bg-card/30 p-6"
              >
                <div
                  className="flex h-10 w-10 items-center justify-center rounded-xl"
                  style={{ background: card.iconBg }}
                >
                  <Icon className="h-5 w-5" style={{ color: card.iconColor }} />
                </div>
                <p className="text-base font-semibold leading-6 text-foreground">
                  {card.title()}
                </p>
                <p className="text-[14px] leading-[23px] text-muted-foreground">
                  {card.desc()}
                </p>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

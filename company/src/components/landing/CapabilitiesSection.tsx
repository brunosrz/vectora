import { m } from "#/paraglide/messages";
import { Globe, Network, ShieldCheck } from "lucide-react";

const CARDS = [
  {
    id: "browser",
    Icon: Globe,
    title: m.capability_browser_title,
    desc: m.capability_browser_desc,
    iconBg: "rgba(121,184,255,0.1)",
    iconColor: "var(--primary)",
  },
  {
    id: "sandbox",
    Icon: ShieldCheck,
    title: m.capability_sandbox_title,
    desc: m.capability_sandbox_desc,
    iconBg: "rgba(78,201,160,0.1)",
    iconColor: "var(--accent-green)",
  },
  {
    id: "context-graph",
    Icon: Network,
    title: m.capability_context_graph_title,
    desc: m.capability_context_graph_desc,
    iconBg: "rgba(173,70,255,0.1)",
    iconColor: "var(--accent-purple)",
  },
];

export default function CapabilitiesSection() {
  return (
    <section className="bg-background/50 py-[23px]">
      <div className="mx-auto flex max-w-[1024px] flex-col items-center gap-8 px-4 sm:px-6 lg:px-0">
        <div className="flex flex-col items-center gap-3">
          <h2 className="text-center text-[28px] font-semibold leading-[36px] text-foreground">
            {m.capabilities_heading()}
          </h2>
          <p className="text-center text-base leading-6 text-muted-foreground">
            {m.capabilities_subtitle()}
          </p>
        </div>

        <div className="grid w-full grid-cols-1 gap-5 sm:grid-cols-3">
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

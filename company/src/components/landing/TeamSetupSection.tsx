import { m } from "#/paraglide/messages";
import { Server, User, Users, FolderOpen } from "lucide-react";

const STEPS = [
  {
    Icon: Server,
    titleKey: "team_step1_title" as const,
    descKey: "team_step1_desc" as const,
    iconBg: "rgba(121,184,255,0.1)",
    iconColor: "var(--primary)",
    badges: ["PostgreSQL", "Qdrant", "Redis"],
  },
  {
    Icon: User,
    titleKey: "team_step2_title" as const,
    descKey: "team_step2_desc" as const,
    iconBg: "rgba(173,70,255,0.1)",
    iconColor: "var(--accent-purple)",
  },
  {
    Icon: Users,
    titleKey: "team_step3_title" as const,
    descKey: "team_step3_desc" as const,
    iconBg: "rgba(78,201,160,0.1)",
    iconColor: "var(--accent-green)",
  },
  {
    Icon: FolderOpen,
    titleKey: "team_step4_title" as const,
    descKey: "team_step4_desc" as const,
    iconBg: "rgba(226,192,141,0.1)",
    iconColor: "var(--accent-amber)",
  },
];

export default function TeamSetupSection() {
  return (
    <section className="px-4 py-[23px] sm:px-8">
      <div className="mx-auto flex max-w-[1024px] flex-col items-center gap-[22px]">
        <h2 className="text-center text-[28px] font-semibold leading-[36px] text-foreground">
          {m.team_heading()}
        </h2>

        {/* 4 cards lado a lado */}
        <div className="grid w-full grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {STEPS.map((step, i) => {
            const { Icon } = step;
            return (
              <div
                key={i}
                className="flex flex-col gap-2 rounded-2xl border border-border bg-card/30 p-4"
              >
                {/* Ícone + contador */}
                <div className="flex items-center justify-between">
                  <div
                    className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-border"
                    style={{ background: step.iconBg }}
                  >
                    <Icon
                      className="h-5 w-5"
                      style={{ color: step.iconColor }}
                    />
                  </div>
                  <span className="text-[12px] font-medium text-muted-foreground">
                    {i + 1}/{STEPS.length}
                  </span>
                </div>

                <p className="text-base font-semibold leading-6 text-foreground">
                  {m[step.titleKey]()}
                </p>
                <p className="text-[14px] leading-5 text-muted-foreground">
                  {m[step.descKey]()}
                </p>

                {"badges" in step && step.badges && (
                  <div className="flex items-center justify-between gap-[6px]">
                    {step.badges.map((b) => (
                      <span
                        key={b}
                        className="rounded-lg border border-border bg-card/60 px-[9px] py-0.5 text-[12px] text-muted-foreground"
                      >
                        {b}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Barra de compatibilidade */}
        <div className="rounded-2xl border border-border bg-card/30 px-6 py-4 text-center text-[14px] leading-5 text-muted-foreground">
          {m.team_compat()}
        </div>
      </div>
    </section>
  );
}

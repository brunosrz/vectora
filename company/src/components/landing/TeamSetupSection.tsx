import { m } from "#/paraglide/messages";
import { Server, User, Users, FolderOpen, Check } from "lucide-react";

const EXTRA_BULLETS = [
  m.team_extra_bullet_storage,
  m.team_extra_bullet_access,
  m.team_extra_bullet_automation,
];

const STEPS = [
  {
    Icon: Server,
    title: m.team_step1_title,
    desc: m.team_step1_desc,
    iconBg: "rgba(121,184,255,0.1)",
    iconColor: "var(--primary)",
    badges: ["PostgreSQL", "Qdrant", "Redis"],
  },
  {
    Icon: User,
    title: m.team_step2_title,
    desc: m.team_step2_desc,
    iconBg: "rgba(173,70,255,0.1)",
    iconColor: "var(--accent-purple)",
  },
  {
    Icon: Users,
    title: m.team_step3_title,
    desc: m.team_step3_desc,
    iconBg: "rgba(78,201,160,0.1)",
    iconColor: "var(--accent-green)",
  },
  {
    Icon: FolderOpen,
    title: m.team_step4_title,
    desc: m.team_step4_desc,
    iconBg: "rgba(226,192,141,0.1)",
    iconColor: "var(--accent-amber)",
  },
];

export default function TeamSetupSection() {
  return (
    <section className="px-4 py-[23px] sm:px-6 lg:px-8">
      <div className="mx-auto flex max-w-[1024px] flex-col items-center gap-[22px]">
        <h2 className="text-center text-[28px] font-semibold leading-[36px] text-foreground">
          {m.team_heading()}
        </h2>

        {/* Mobile/tablet: empilhados em largura total. Desktop (lg+): lado a
            lado, largura fixa ditada pela linha de badges. */}
        <div className="flex w-full flex-col gap-2 lg:flex-row lg:flex-wrap lg:justify-center">
          {STEPS.map((step, i) => {
            const { Icon } = step;
            return (
              <div
                key={i}
                className="flex w-full flex-col gap-2 rounded-2xl border border-border bg-card/30 p-3 lg:w-[248px] lg:shrink-0"
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
                  {step.title()}
                </p>
                <p className="text-[14px] leading-5 text-muted-foreground">
                  {step.desc()}
                </p>

                {"badges" in step && step.badges && (
                  <div className="flex items-center gap-1.5">
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

        {/* Reforço do que o Pro entrega além do fluxo de setup acima —
            eficiência do storage completo, controle de acesso em escala,
            automação — não é só "sobe mais rápido", é operar diferente. */}
        <div className="w-full rounded-2xl border border-primary/20 bg-primary/5 p-5">
          <p className="mb-3 text-center text-[15px] font-semibold text-foreground">
            {m.team_extra_heading()}
          </p>
          <ul className="mx-auto flex max-w-[720px] flex-col gap-2.5">
            {EXTRA_BULLETS.map((bullet) => (
              <li
                key={bullet()}
                className="flex items-start gap-2.5 text-[14px] leading-5 text-muted-foreground"
              >
                <Check className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
                <span>{bullet()}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}

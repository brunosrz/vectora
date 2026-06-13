import { m } from "#/paraglide/messages";
import { Server, User, Users, FolderOpen } from "lucide-react";

interface Step {
  icon: typeof Server;
  titleKey: keyof typeof m;
  descKey: keyof typeof m;
  color: string;
  border: string;
  bg: string;
  visual: React.ReactNode;
  badges?: string[];
}

const STEPS: Step[] = [
  {
    icon: Server,
    titleKey: "team_step1_title",
    descKey: "team_step1_desc",
    color: "text-primary",
    border: "border-primary",
    bg: "bg-primary/10",
    visual: (
      <div className="mt-3 rounded-lg bg-background border border-border px-4 py-3 font-mono text-sm text-primary select-none">
        <span className="text-muted-foreground">$ </span>docker compose up -d
        <div className="mt-1 text-xs text-muted-foreground space-y-0.5">
          <div>✓ vectora running</div>
          <div>✓ postgresql running</div>
          <div>✓ redis running</div>
        </div>
      </div>
    ),
    badges: ["Vectora", "PostgreSQL", "Redis"],
  },
  {
    icon: User,
    titleKey: "team_step2_title",
    descKey: "team_step2_desc",
    color: "text-accent-purple",
    border: "border-purple-500",
    bg: "bg-purple-500/10",
    visual: (
      <div
        className="mt-3 overflow-hidden rounded-lg border border-border gif-skeleton"
        style={{ aspectRatio: "16/9", maxWidth: 400 }}
      >
        <img
          src="/gifs/setup-root.gif"
          alt="First-time root setup"
          loading="lazy"
          decoding="async"
          className="h-full w-full object-cover"
          onLoad={(e) => (e.currentTarget.style.background = "none")}
        />
      </div>
    ),
  },
  {
    icon: Users,
    titleKey: "team_step3_title",
    descKey: "team_step3_desc",
    color: "text-accent-green",
    border: "border-green-500",
    bg: "bg-accent-green/10",
    visual: (
      <div
        className="mt-3 overflow-hidden rounded-lg border border-border gif-skeleton"
        style={{ aspectRatio: "16/9", maxWidth: 400 }}
      >
        <img
          src="/gifs/setup-invite.gif"
          alt="Invite team members"
          loading="lazy"
          decoding="async"
          className="h-full w-full object-cover"
          onLoad={(e) => (e.currentTarget.style.background = "none")}
        />
      </div>
    ),
  },
  {
    icon: FolderOpen,
    titleKey: "team_step4_title",
    descKey: "team_step4_desc",
    color: "text-accent-amber",
    border: "border-amber-500",
    bg: "bg-accent-amber/10",
    visual: (
      <div
        className="mt-3 overflow-hidden rounded-lg border border-border gif-skeleton"
        style={{ aspectRatio: "16/9", maxWidth: 400 }}
      >
        <img
          src="/gifs/setup-project.gif"
          alt="Create project and start chatting"
          loading="lazy"
          decoding="async"
          className="h-full w-full object-cover"
          onLoad={(e) => (e.currentTarget.style.background = "none")}
        />
      </div>
    ),
  },
];

const COMPAT_ICONS = ["PostgreSQL", "Redis", "Docker"];

export default function TeamSetupSection() {
  return (
    <section className="bg-background/50 px-4 py-10 sm:px-6 sm:py-14 lg:px-8">
      <div className="mx-auto max-w-6xl">
        <div className="mb-10 text-center">
          <h2 className="mb-3 text-2xl font-semibold text-foreground sm:text-3xl">
            {m.team_heading()}
          </h2>
        </div>

        {/* Grid horizontal: 4 etapas lado a lado (1 col mobile, 2 tablet, 4 desktop) */}
        <ol className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {STEPS.map((step, i) => {
            const Icon = step.icon;
            const titleFn = m[step.titleKey] as (() => string) | undefined;
            const descFn = m[step.descKey] as (() => string) | undefined;
            return (
              <li
                key={i}
                className="flex flex-col rounded-xl border border-border bg-card/30 p-5"
              >
                <div className="mb-3 flex items-center justify-between">
                  <div
                    className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full border ${step.border} ${step.bg}`}
                  >
                    <Icon className={`h-5 w-5 ${step.color}`} />
                  </div>
                  <span className="text-xs font-bold text-muted-foreground">
                    {i + 1}/{STEPS.length}
                  </span>
                </div>
                <p className="mb-1 font-semibold text-foreground">
                  {titleFn?.()}
                </p>
                <p className="text-sm text-muted-foreground">{descFn?.()}</p>
                {step.badges && (
                  <div className="mt-3 flex flex-wrap gap-1.5">
                    {step.badges.map((b) => (
                      <span
                        key={b}
                        className="rounded-md border border-border bg-card/60 px-2 py-0.5 text-xs text-muted-foreground"
                      >
                        {b}
                      </span>
                    ))}
                  </div>
                )}
              </li>
            );
          })}
        </ol>

        <div className="mt-10 rounded-xl border border-border bg-card/30 px-6 py-4 flex flex-col sm:flex-row items-center gap-3 text-center sm:text-left">
          <div className="flex gap-2">
            {COMPAT_ICONS.map((ic) => (
              <span
                key={ic}
                className="rounded border border-border bg-background px-2 py-0.5 text-xs text-foreground/90"
              >
                {ic}
              </span>
            ))}
          </div>
          <p className="text-sm text-muted-foreground">{m.team_compat()}</p>
        </div>
      </div>
    </section>
  );
}

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
    color: "text-brand-400",
    border: "border-brand-500",
    bg: "bg-brand-500/10",
    visual: (
      <div className="mt-3 rounded-lg bg-brand-950 border border-brand-800 px-4 py-3 font-mono text-sm text-brand-300 select-none">
        <span className="text-slate-500">$ </span>docker compose up -d
        <div className="mt-1 text-xs text-slate-500 space-y-0.5">
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
    color: "text-purple-400",
    border: "border-purple-500",
    bg: "bg-purple-500/10",
    visual: (
      <div
        className="mt-3 overflow-hidden rounded-lg border border-brand-700 gif-skeleton"
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
    color: "text-green-400",
    border: "border-green-500",
    bg: "bg-green-500/10",
    visual: (
      <div
        className="mt-3 overflow-hidden rounded-lg border border-brand-700 gif-skeleton"
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
    color: "text-amber-400",
    border: "border-amber-500",
    bg: "bg-amber-500/10",
    visual: (
      <div
        className="mt-3 overflow-hidden rounded-lg border border-brand-700 gif-skeleton"
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
    <section className="bg-brand-900/50 px-4 py-20 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-4xl">
        <div className="mb-14 text-center">
          <h2 className="mb-3 text-3xl font-semibold text-white sm:text-4xl">
            {m.team_heading()}
          </h2>
        </div>

        <div className="relative">
          <div
            className="absolute left-5 top-0 h-full w-px bg-brand-800 sm:left-6"
            aria-hidden
          />

          <ol className="space-y-10">
            {STEPS.map((step, i) => {
              const Icon = step.icon;
              const titleFn = m[step.titleKey] as (() => string) | undefined;
              const descFn = m[step.descKey] as (() => string) | undefined;
              return (
                <li key={i} className="relative flex gap-5 sm:gap-6">
                  <div
                    className={`relative z-10 flex h-10 w-10 shrink-0 sm:h-12 sm:w-12 items-center justify-center rounded-full border ${step.border} ${step.bg}`}
                  >
                    <Icon className={`h-4 w-4 sm:h-5 sm:w-5 ${step.color}`} />
                    <span className="absolute -top-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full bg-brand-700 text-[9px] font-bold text-slate-300">
                      {i + 1}
                    </span>
                  </div>

                  <div className="flex-1 pt-1.5">
                    <p className="mb-1 font-semibold text-white">
                      {titleFn?.()}
                    </p>
                    <p className="text-sm text-slate-400">{descFn?.()}</p>
                    {step.visual}
                    {step.badges && (
                      <div className="mt-2 flex flex-wrap gap-1.5">
                        {step.badges.map((b) => (
                          <span
                            key={b}
                            className="rounded-md border border-brand-700 bg-brand-800/60 px-2 py-0.5 text-xs text-slate-400"
                          >
                            {b}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </li>
              );
            })}
          </ol>
        </div>

        <div className="mt-14 rounded-xl border border-brand-700 bg-brand-800/30 px-6 py-4 flex flex-col sm:flex-row items-center gap-3 text-center sm:text-left">
          <div className="flex gap-2">
            {COMPAT_ICONS.map((ic) => (
              <span
                key={ic}
                className="rounded border border-brand-700 bg-brand-900 px-2 py-0.5 text-xs text-slate-300"
              >
                {ic}
              </span>
            ))}
          </div>
          <p className="text-sm text-slate-400">{m.team_compat()}</p>
        </div>
      </div>
    </section>
  );
}

import { m } from "#/paraglide/messages";

interface AgentBoxProps {
  title: string;
  sub: string;
  colorVar: string;
}

/** Caixa flexível do diagrama — cresce com o texto, nada vaza. */
function AgentBox({ title, sub, colorVar }: AgentBoxProps) {
  return (
    <div
      className="flex min-w-0 flex-col items-center justify-center rounded-lg border px-3 py-2 text-center"
      style={{
        borderColor: `var(${colorVar})`,
        background: `color-mix(in srgb, var(${colorVar}) 14%, var(--card))`,
        color: `var(${colorVar})`,
      }}
    >
      <span className="text-sm font-semibold">{title}</span>
      <span className="text-[11px] opacity-90">{sub}</span>
    </div>
  );
}

function AgenticDiagram() {
  return (
    <div className="rounded-xl border border-border bg-card/40 p-6" aria-hidden>
      <div className="flex flex-col items-center gap-1.5">
        <span className="text-xs text-muted-foreground">Resposta</span>
        <span className="text-sm leading-none text-muted-foreground">↑</span>

        <div className="rounded-lg border border-border bg-card px-5 py-2 text-sm text-muted-foreground">
          Usuário
        </div>

        <span className="text-sm leading-none text-muted-foreground">↓</span>

        <div
          className="flex flex-col items-center rounded-lg border-2 px-6 py-2 text-center"
          style={{
            borderColor: "var(--primary)",
            background: "var(--muted)",
            color: "var(--primary)",
          }}
        >
          <span className="text-sm font-semibold">Orchestrator</span>
          <span className="text-[11px] opacity-90">
            decide · delega · paraleliza
          </span>
        </div>

        {/* Conector orchestrator → agentes (escala com a largura) */}
        <svg
          className="h-8 w-full"
          viewBox="0 0 300 32"
          preserveAspectRatio="none"
        >
          <line
            x1="150"
            y1="2"
            x2="50"
            y2="30"
            stroke="var(--primary)"
            strokeWidth="1.5"
          />
          <line
            x1="150"
            y1="2"
            x2="150"
            y2="30"
            stroke="var(--accent-purple)"
            strokeWidth="1.5"
          />
          <line
            x1="150"
            y1="2"
            x2="250"
            y2="30"
            stroke="var(--accent-green)"
            strokeWidth="1.5"
          />
        </svg>

        <div className="grid w-full grid-cols-3 gap-3">
          <AgentBox
            title="Coder Agent"
            sub="fs · terminal · git"
            colorVar="--primary"
          />
          <AgentBox
            title="Search Agent"
            sub="web · RAG · curadoria"
            colorVar="--accent-purple"
          />
          <AgentBox
            title="RAG Subgraph"
            sub="expand · rerank · inject"
            colorVar="--accent-green"
          />
        </div>
      </div>
    </div>
  );
}

const BULLETS = [
  m.agentic_bullet_orchestrator,
  m.agentic_bullet_coder,
  m.agentic_bullet_search,
  m.agentic_bullet_rag,
  m.agentic_bullet_parallel,
];

export default function AgenticFlowSection() {
  return (
    <section className="bg-background/50 px-4 py-10 sm:px-6 sm:py-14 lg:px-8">
      <div className="mx-auto max-w-6xl">
        <div className="grid grid-cols-1 items-center gap-10 lg:grid-cols-2">
          <AgenticDiagram />

          <div>
            <h2 className="mb-6 text-2xl font-semibold text-foreground sm:text-3xl">
              {m.agentic_heading()}
            </h2>
            <ul className="mb-8 space-y-3">
              {BULLETS.map((fn, i) => (
                <li
                  key={i}
                  className="flex items-start gap-3 text-sm text-muted-foreground"
                >
                  <span className="mt-0.5 h-5 w-5 shrink-0 rounded-full bg-primary/20 flex items-center justify-center text-primary text-xs font-bold">
                    {i + 1}
                  </span>
                  {fn()}
                </li>
              ))}
            </ul>
            <a
              href="https://docs.vectora.company"
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm font-medium text-primary hover:text-primary transition-colors"
            >
              {m.agentic_docs_link()}
            </a>
          </div>
        </div>
      </div>
    </section>
  );
}

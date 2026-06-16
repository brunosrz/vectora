import { m } from "#/paraglide/messages";

interface AgentBoxProps {
  title: string;
  sub: string;
  color: string;
}

function AgentBox({ title, sub, color }: AgentBoxProps) {
  return (
    <div
      className="flex flex-1 flex-col items-center justify-center rounded-xl py-2 text-center"
      style={{ border: `0.666667px solid ${color}`, color }}
    >
      <span className="w-full text-[14px] font-semibold leading-5">
        {title}
      </span>
      <span className="w-full text-[11px] leading-4">{sub}</span>
    </div>
  );
}

function AgenticDiagram() {
  return (
    <div
      className="flex flex-col items-center justify-center gap-1.5 rounded-2xl border border-border bg-card/40 p-6"
      aria-hidden
    >
      <span className="text-[12px] leading-4 text-muted-foreground">
        Resposta
      </span>
      <span className="text-[14px] leading-none text-muted-foreground">↑</span>

      <div className="rounded-xl border border-border bg-card px-5 py-2 text-[14px] leading-5 text-muted-foreground">
        Usuário
      </div>

      <span className="text-[14px] leading-none text-muted-foreground">↓</span>

      <div
        className="flex flex-col items-center rounded-xl border-2 px-6 py-2 text-center"
        style={{ borderColor: "var(--primary)", background: "#262626" }}
      >
        <span className="text-[14px] font-semibold leading-5 text-primary">
          Orchestrator
        </span>
        <span className="text-[11px] leading-4 text-primary opacity-90">
          decide · delega · paraleliza
        </span>
      </div>

      {/* Linhas de conexão: azul → Coder, roxo → Search, verde → RAG */}
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
          strokeWidth="1.95"
        />
        <line
          x1="150"
          y1="2"
          x2="150"
          y2="30"
          stroke="var(--accent-purple)"
          strokeWidth="1.95"
        />
        <line
          x1="150"
          y1="2"
          x2="250"
          y2="30"
          stroke="var(--accent-green)"
          strokeWidth="1.95"
        />
      </svg>

      <div className="flex w-full gap-[25px]">
        <AgentBox
          title="Coder Agent"
          sub="fs · terminal · git"
          color="var(--primary)"
        />
        <AgentBox
          title="Search Agent"
          sub="web · RAG · curadoria"
          color="var(--accent-purple)"
        />
        <AgentBox
          title="RAG Subgraph"
          sub="expand · rerank · inject"
          color="var(--accent-green)"
        />
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
    <section className="px-4 py-[23px] sm:px-8">
      <div className="mx-auto grid max-w-[1024px] grid-cols-1 gap-8 lg:grid-cols-2 lg:items-center">
        <AgenticDiagram />

        <div className="flex flex-col justify-center gap-6">
          <h2 className="text-[28px] font-semibold leading-[36px] text-foreground">
            {m.agentic_heading()}
          </h2>

          <ul className="flex flex-col">
            {BULLETS.map((fn, i) => (
              <li
                key={i}
                className={`flex items-start gap-3 text-[14px] leading-5 text-muted-foreground${i > 0 ? " pt-3" : ""}`}
              >
                <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-primary/20 text-[12px] font-medium text-primary">
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
            className="text-[14px] font-medium leading-5 text-primary transition-colors hover:text-primary/80"
          >
            {m.agentic_docs_link()}
          </a>
        </div>
      </div>
    </section>
  );
}

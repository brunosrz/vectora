import { m } from "#/paraglide/messages";

function AgenticDiagram() {
  return (
    <div className="rounded-xl border border-border bg-card/40 p-6">
      <svg
        viewBox="0 0 420 320"
        className="w-full"
        aria-hidden
        style={{ fontFamily: "inherit" }}
      >
        {/* Orchestrator — center */}
        <rect
          x="140"
          y="120"
          width="140"
          height="48"
          rx="10"
          fill="var(--muted)"
          stroke="var(--primary)"
          strokeWidth="2"
        />
        <text
          x="210"
          y="138"
          textAnchor="middle"
          fill="var(--primary)"
          fontSize="11"
          fontWeight="600"
        >
          Orchestrator
        </text>
        <text
          x="210"
          y="155"
          textAnchor="middle"
          fill="var(--primary)"
          fontSize="9"
        >
          decide · delega · paraleliza
        </text>

        {/* User */}
        <rect
          x="157"
          y="28"
          width="106"
          height="38"
          rx="8"
          fill="var(--card)"
          stroke="var(--border)"
          strokeWidth="1.5"
        />
        <text
          x="210"
          y="51"
          textAnchor="middle"
          fill="var(--muted-foreground)"
          fontSize="11"
        >
          Usuário
        </text>

        {/* Arrow down user→orch */}
        <line
          x1="210"
          y1="66"
          x2="210"
          y2="120"
          stroke="var(--border)"
          strokeWidth="1.5"
          markerEnd="url(#arr)"
        />

        {/* Coder Agent */}
        <rect
          x="16"
          y="214"
          width="110"
          height="40"
          rx="8"
          fill="var(--muted)"
          stroke="var(--primary)"
          strokeWidth="1.5"
        />
        <text
          x="71"
          y="232"
          textAnchor="middle"
          fill="var(--primary)"
          fontSize="10"
          fontWeight="600"
        >
          Coder Agent
        </text>
        <text
          x="71"
          y="246"
          textAnchor="middle"
          fill="var(--primary)"
          fontSize="8"
        >
          fs · terminal · git
        </text>

        {/* Search Agent */}
        <rect
          x="155"
          y="214"
          width="110"
          height="40"
          rx="8"
          fill="color-mix(in srgb, var(--accent-purple) 18%, var(--card))"
          stroke="var(--accent-purple)"
          strokeWidth="1.5"
        />
        <text
          x="210"
          y="232"
          textAnchor="middle"
          fill="var(--accent-purple)"
          fontSize="10"
          fontWeight="600"
        >
          Search Agent
        </text>
        <text
          x="210"
          y="246"
          textAnchor="middle"
          fill="var(--accent-purple)"
          fontSize="8"
        >
          web · RAG · curadoria
        </text>

        {/* RAG Subgraph */}
        <rect
          x="294"
          y="214"
          width="110"
          height="40"
          rx="8"
          fill="color-mix(in srgb, var(--accent-green) 18%, var(--card))"
          stroke="var(--accent-green)"
          strokeWidth="1.5"
        />
        <text
          x="349"
          y="232"
          textAnchor="middle"
          fill="var(--accent-green)"
          fontSize="10"
          fontWeight="600"
        >
          RAG Subgraph
        </text>
        <text
          x="349"
          y="246"
          textAnchor="middle"
          fill="var(--accent-green)"
          fontSize="8"
        >
          expand · rerank · inject
        </text>

        {/* Lines orch → agents */}
        <line
          x1="175"
          y1="168"
          x2="71"
          y2="214"
          stroke="var(--primary)"
          strokeWidth="1.5"
          markerEnd="url(#arrb)"
        />
        <line
          x1="210"
          y1="168"
          x2="210"
          y2="214"
          stroke="var(--accent-purple)"
          strokeWidth="1.5"
          markerEnd="url(#arrp)"
        />
        <line
          x1="245"
          y1="168"
          x2="349"
          y2="214"
          stroke="var(--accent-green)"
          strokeWidth="1.5"
          markerEnd="url(#arrg)"
        />

        {/* Response arrow up */}
        <line
          x1="210"
          y1="26"
          x2="210"
          y2="8"
          stroke="var(--border)"
          strokeWidth="1.5"
          markerEnd="url(#arr)"
        />
        <text
          x="210"
          y="6"
          textAnchor="middle"
          fill="var(--muted-foreground)"
          fontSize="9"
        >
          Resposta
        </text>

        {/* Arrow markers */}
        <defs>
          <marker
            id="arr"
            markerWidth="8"
            markerHeight="8"
            refX="4"
            refY="4"
            orient="auto"
          >
            <path d="M0,0 L0,8 L8,4 z" fill="var(--border)" />
          </marker>
          <marker
            id="arrb"
            markerWidth="8"
            markerHeight="8"
            refX="4"
            refY="4"
            orient="auto"
          >
            <path d="M0,0 L0,8 L8,4 z" fill="var(--primary)" />
          </marker>
          <marker
            id="arrp"
            markerWidth="8"
            markerHeight="8"
            refX="4"
            refY="4"
            orient="auto"
          >
            <path d="M0,0 L0,8 L8,4 z" fill="var(--accent-purple)" />
          </marker>
          <marker
            id="arrg"
            markerWidth="8"
            markerHeight="8"
            refX="4"
            refY="4"
            orient="auto"
          >
            <path d="M0,0 L0,8 L8,4 z" fill="var(--accent-green)" />
          </marker>
        </defs>
      </svg>
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
    <section className="bg-background/50 px-4 py-14 sm:px-6 sm:py-20 lg:px-8">
      <div className="mx-auto max-w-6xl">
        <div className="grid grid-cols-1 items-center gap-12 lg:grid-cols-2">
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

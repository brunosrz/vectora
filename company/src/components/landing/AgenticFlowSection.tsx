import { m } from "#/paraglide/messages";

function AgenticDiagram() {
  return (
    <div className="rounded-xl border border-brand-700 bg-brand-800/40 p-6">
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
          fill="#1e3a5f"
          stroke="#3b82f6"
          strokeWidth="2"
        />
        <text
          x="210"
          y="138"
          textAnchor="middle"
          fill="#93c5fd"
          fontSize="11"
          fontWeight="600"
        >
          Orchestrator
        </text>
        <text x="210" y="155" textAnchor="middle" fill="#60a5fa" fontSize="9">
          decide · delega · paraleliza
        </text>

        {/* User */}
        <rect
          x="157"
          y="28"
          width="106"
          height="38"
          rx="8"
          fill="#0a0e1a"
          stroke="#475569"
          strokeWidth="1.5"
        />
        <text x="210" y="51" textAnchor="middle" fill="#94a3b8" fontSize="11">
          Usuário
        </text>

        {/* Arrow down user→orch */}
        <line
          x1="210"
          y1="66"
          x2="210"
          y2="120"
          stroke="#475569"
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
          fill="#1e3a5f"
          stroke="#2563eb"
          strokeWidth="1.5"
        />
        <text
          x="71"
          y="232"
          textAnchor="middle"
          fill="#93c5fd"
          fontSize="10"
          fontWeight="600"
        >
          Coder Agent
        </text>
        <text x="71" y="246" textAnchor="middle" fill="#60a5fa" fontSize="8">
          fs · terminal · git
        </text>

        {/* Search Agent */}
        <rect
          x="155"
          y="214"
          width="110"
          height="40"
          rx="8"
          fill="#2e1b5e"
          stroke="#7c3aed"
          strokeWidth="1.5"
        />
        <text
          x="210"
          y="232"
          textAnchor="middle"
          fill="#c4b5fd"
          fontSize="10"
          fontWeight="600"
        >
          Search Agent
        </text>
        <text x="210" y="246" textAnchor="middle" fill="#a78bfa" fontSize="8">
          web · RAG · curadoria
        </text>

        {/* RAG Subgraph */}
        <rect
          x="294"
          y="214"
          width="110"
          height="40"
          rx="8"
          fill="#064e3b"
          stroke="#059669"
          strokeWidth="1.5"
        />
        <text
          x="349"
          y="232"
          textAnchor="middle"
          fill="#6ee7b7"
          fontSize="10"
          fontWeight="600"
        >
          RAG Subgraph
        </text>
        <text x="349" y="246" textAnchor="middle" fill="#34d399" fontSize="8">
          expand · rerank · inject
        </text>

        {/* Lines orch → agents */}
        <line
          x1="175"
          y1="168"
          x2="71"
          y2="214"
          stroke="#2563eb"
          strokeWidth="1.5"
          markerEnd="url(#arrb)"
        />
        <line
          x1="210"
          y1="168"
          x2="210"
          y2="214"
          stroke="#7c3aed"
          strokeWidth="1.5"
          markerEnd="url(#arrp)"
        />
        <line
          x1="245"
          y1="168"
          x2="349"
          y2="214"
          stroke="#059669"
          strokeWidth="1.5"
          markerEnd="url(#arrg)"
        />

        {/* Response arrow up */}
        <line
          x1="210"
          y1="26"
          x2="210"
          y2="8"
          stroke="#475569"
          strokeWidth="1.5"
          markerEnd="url(#arr)"
        />
        <text x="210" y="6" textAnchor="middle" fill="#94a3b8" fontSize="9">
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
            <path d="M0,0 L0,8 L8,4 z" fill="#475569" />
          </marker>
          <marker
            id="arrb"
            markerWidth="8"
            markerHeight="8"
            refX="4"
            refY="4"
            orient="auto"
          >
            <path d="M0,0 L0,8 L8,4 z" fill="#2563eb" />
          </marker>
          <marker
            id="arrp"
            markerWidth="8"
            markerHeight="8"
            refX="4"
            refY="4"
            orient="auto"
          >
            <path d="M0,0 L0,8 L8,4 z" fill="#7c3aed" />
          </marker>
          <marker
            id="arrg"
            markerWidth="8"
            markerHeight="8"
            refX="4"
            refY="4"
            orient="auto"
          >
            <path d="M0,0 L0,8 L8,4 z" fill="#059669" />
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
    <section className="bg-brand-900/50 px-4 py-20 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-6xl">
        <div className="grid grid-cols-1 items-center gap-12 lg:grid-cols-2">
          <AgenticDiagram />

          <div>
            <h2 className="mb-6 text-3xl font-semibold text-white sm:text-4xl">
              {m.agentic_heading()}
            </h2>
            <ul className="mb-8 space-y-3">
              {BULLETS.map((fn, i) => (
                <li
                  key={i}
                  className="flex items-start gap-3 text-sm text-slate-400"
                >
                  <span className="mt-0.5 h-5 w-5 shrink-0 rounded-full bg-brand-500/20 flex items-center justify-center text-brand-400 text-xs font-bold">
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
              className="text-sm font-medium text-brand-400 hover:text-brand-300 transition-colors"
            >
              {m.agentic_docs_link()}
            </a>
          </div>
        </div>
      </div>
    </section>
  );
}

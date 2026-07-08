import { m } from "#/paraglide/messages";

const BULLETS = [
  m.rag_bullet_formats,
  m.rag_bullet_embeddings,
  m.rag_bullet_search,
  m.rag_bullet_rerank,
  m.rag_bullet_indexing,
  m.rag_bullet_curator,
  m.rag_bullet_citation,
];

function RagDiagram() {
  return (
    <div
      className="flex h-full items-center justify-center rounded-2xl border border-border bg-card/40 p-6"
      aria-hidden
    >
      <svg
        viewBox="0 0 400 280"
        className="w-full"
        style={{ fontFamily: "inherit" }}
      >
        {/* Left column: Documento → Chunking → LanceDB */}
        {[
          { y: 30, label: "Documento", sub: "PDF · MD · código" },
          { y: 100, label: "Chunking", sub: "→ embeddings" },
        ].map((item) => (
          <g key={item.label}>
            <rect
              x="35"
              y={item.y - 18}
              width="110"
              height="38"
              rx="8"
              fill="var(--node-surface)"
              stroke="var(--primary)"
              strokeWidth="1.9"
            />
            <text
              x="90"
              y={item.y - 2}
              textAnchor="middle"
              fill="var(--primary)"
              fontSize="11"
              fontWeight="700"
            >
              {item.label}
            </text>
            <text
              x="90"
              y={item.y + 11}
              textAnchor="middle"
              fill="var(--primary)"
              fontSize="9"
            >
              {item.sub}
            </text>
          </g>
        ))}

        {/* LanceDB — cylinder (vector store) */}
        <ellipse
          cx="90"
          cy="160"
          rx="55"
          ry="9"
          fill="color-mix(in srgb, var(--accent-green) 18%, var(--node-surface))"
          stroke="var(--accent-green)"
          strokeWidth="1.9"
        />
        <rect
          x="35"
          y="160"
          width="110"
          height="26"
          fill="color-mix(in srgb, var(--accent-green) 18%, var(--node-surface))"
        />
        <ellipse
          cx="90"
          cy="186"
          rx="55"
          ry="9"
          fill="color-mix(in srgb, var(--accent-green) 18%, var(--node-surface))"
          stroke="var(--accent-green)"
          strokeWidth="1.9"
        />
        <text
          x="90"
          y="174"
          textAnchor="middle"
          fill="var(--accent-green)"
          fontSize="11"
          fontWeight="700"
        >
          LanceDB
        </text>
        <text
          x="90"
          y="186"
          textAnchor="middle"
          fill="var(--accent-green)"
          fontSize="9"
        >
          vector store
        </text>

        {/* Left connectors */}
        <line
          x1="90"
          y1="50"
          x2="90"
          y2="82"
          stroke="var(--primary)"
          strokeWidth="1.9"
        />
        <line
          x1="90"
          y1="120"
          x2="90"
          y2="151"
          stroke="var(--primary)"
          strokeWidth="1.9"
        />

        {/* Right column: Query → Hybrid Search → Reranker */}
        {[
          {
            y: 30,
            label: "Query",
            sub: "pergunta do usuário",
            fill: "color-mix(in srgb, var(--accent-purple) 16%, var(--node-surface))",
            stroke: "var(--accent-purple)",
            textFill: "var(--accent-purple)",
          },
          {
            y: 100,
            label: "Busca vetorial",
            sub: "densa · +BM25 no Completo",
            fill: "var(--node-surface)",
            stroke: "var(--primary)",
            textFill: "var(--primary)",
          },
          {
            y: 170,
            label: "Reranker",
            sub: "Cohere/Voyage (opcional)",
            fill: "color-mix(in srgb, var(--accent-amber) 16%, var(--node-surface))",
            stroke: "var(--accent-amber)",
            textFill: "var(--accent-amber)",
          },
        ].map((item) => (
          <g key={item.label}>
            <rect
              x="185"
              y={item.y - 18}
              width="120"
              height="38"
              rx="8"
              fill={item.fill}
              stroke={item.stroke}
              strokeWidth="1.9"
            />
            <text
              x="245"
              y={item.y - 2}
              textAnchor="middle"
              fill={item.textFill}
              fontSize="11"
              fontWeight="700"
            >
              {item.label}
            </text>
            <text
              x="245"
              y={item.y + 11}
              textAnchor="middle"
              fill={item.textFill}
              fontSize="9"
            >
              {item.sub}
            </text>
          </g>
        ))}

        {/* Right connectors */}
        <line
          x1="245"
          y1="50"
          x2="245"
          y2="82"
          stroke="var(--accent-purple)"
          strokeWidth="1.9"
        />
        <line
          x1="245"
          y1="120"
          x2="245"
          y2="152"
          stroke="var(--primary)"
          strokeWidth="1.9"
        />

        {/* Bridge: LanceDB → Hybrid Search (dashed green) */}
        <line
          x1="145"
          y1="167"
          x2="185"
          y2="112"
          stroke="var(--accent-green)"
          strokeWidth="1.27"
          strokeDasharray="4,3"
        />

        {/* LLM box */}
        <rect
          x="140"
          y="218"
          width="120"
          height="42"
          rx="8"
          fill="var(--node-surface)"
          stroke="var(--primary)"
          strokeWidth="2.53"
        />
        <text
          x="200"
          y="236"
          textAnchor="middle"
          fill="var(--primary)"
          fontSize="11"
          fontWeight="700"
        >
          LLM
        </text>
        <text
          x="200"
          y="250"
          textAnchor="middle"
          fill="var(--primary)"
          fontSize="9"
        >
          contexto + resposta
        </text>

        {/* Reranker → LLM */}
        <line
          x1="245"
          y1="190"
          x2="240"
          y2="218"
          stroke="var(--accent-amber)"
          strokeWidth="1.9"
        />
      </svg>
    </div>
  );
}

export default function RagFlowSection() {
  return (
    <section className="bg-background/50 py-[23px]">
      <div className="mx-auto grid max-w-[1024px] grid-cols-1 gap-8 px-4 sm:px-6 lg:grid-cols-2 lg:items-stretch lg:px-0">
        {/* Text — esquerda */}
        <div className="flex flex-col gap-5">
          <h2 className="text-[28px] font-semibold leading-[36px] text-foreground">
            {m.rag_heading()}
          </h2>
          <ul className="flex flex-col">
            {BULLETS.map((fn, i) => (
              <li
                key={i}
                className={`flex items-start gap-[10px] text-[14px] leading-5 text-muted-foreground${i > 0 ? " pt-[10px]" : ""}`}
              >
                <span className="flex w-[6px] shrink-0 pt-1">
                  <span className="h-1.5 w-1.5 rounded-full bg-primary" />
                </span>
                {fn()}
              </li>
            ))}
          </ul>
        </div>

        {/* Diagrama — direita */}
        <RagDiagram />
      </div>
    </section>
  );
}

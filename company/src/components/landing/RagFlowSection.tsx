import { m } from "#/paraglide/messages";

function RagDiagram() {
  return (
    <div className="rounded-xl border border-border bg-card/40 p-6">
      <svg
        viewBox="0 0 400 280"
        className="w-full"
        aria-hidden
        style={{ fontFamily: "inherit" }}
      >
        {/* Stage labels */}
        {[
          { x: 20, y: 30, label: "Documento", sub: "PDF · MD · código" },
          { x: 20, y: 100, label: "Chunking", sub: "→ Cohere Embed" },
          {
            x: 20,
            y: 170,
            label: "LanceDB",
            sub: "vector store",
            cylinder: true,
          },
        ].map((item) => (
          <g key={item.label}>
            {item.cylinder ? (
              <>
                <ellipse
                  cx="90"
                  cy={item.y - 8}
                  rx="55"
                  ry="10"
                  fill="color-mix(in srgb, var(--accent-green) 18%, var(--card))"
                  stroke="var(--accent-green)"
                  strokeWidth="1.5"
                />
                <rect
                  x="35"
                  y={item.y - 8}
                  width="110"
                  height="32"
                  fill="color-mix(in srgb, var(--accent-green) 18%, var(--card))"
                  stroke="none"
                />
                <ellipse
                  cx="90"
                  cy={item.y + 24}
                  rx="55"
                  ry="10"
                  fill="color-mix(in srgb, var(--accent-green) 18%, var(--card))"
                  stroke="var(--accent-green)"
                  strokeWidth="1.5"
                />
                <text
                  x="90"
                  y={item.y + 10}
                  textAnchor="middle"
                  fill="var(--accent-green)"
                  fontSize="11"
                  fontWeight="600"
                >
                  {item.label}
                </text>
                <text
                  x="90"
                  y={item.y + 23}
                  textAnchor="middle"
                  fill="var(--accent-green)"
                  fontSize="8"
                >
                  {item.sub}
                </text>
              </>
            ) : (
              <>
                <rect
                  x="35"
                  y={item.y - 18}
                  width="110"
                  height="38"
                  rx="8"
                  fill="var(--muted)"
                  stroke="var(--primary)"
                  strokeWidth="1.5"
                />
                <text
                  x="90"
                  y={item.y - 2}
                  textAnchor="middle"
                  fill="var(--primary)"
                  fontSize="11"
                  fontWeight="600"
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
              </>
            )}
          </g>
        ))}

        {/* Arrows left column */}
        <line
          x1="90"
          y1="50"
          x2="90"
          y2="82"
          stroke="var(--primary)"
          strokeWidth="1.5"
          markerEnd="url(#ra)"
        />
        <line
          x1="90"
          y1="120"
          x2="90"
          y2="152"
          stroke="var(--primary)"
          strokeWidth="1.5"
          markerEnd="url(#ra)"
        />

        {/* Right column — query flow */}
        {[
          {
            x: 240,
            y: 30,
            label: "Query",
            sub: "multi-query expand",
            color: "var(--accent-purple)",
            stroke: "var(--accent-purple)",
          },
          {
            x: 240,
            y: 100,
            label: "Hybrid Search",
            sub: "dense + BM25 + RRF",
            color: "var(--muted)",
            stroke: "var(--primary)",
          },
          {
            x: 240,
            y: 170,
            label: "Reranker",
            sub: "Cohere rerank",
            color: "color-mix(in srgb, var(--accent-amber) 18%, var(--card))",
            stroke: "var(--accent-amber)",
          },
        ].map((item) => (
          <g key={item.label}>
            <rect
              x="185"
              y={item.y - 18}
              width="120"
              height="38"
              rx="8"
              fill={item.color}
              stroke={item.stroke}
              strokeWidth="1.5"
            />
            <text
              x="245"
              y={item.y - 2}
              textAnchor="middle"
              fill="var(--foreground)"
              fontSize="11"
              fontWeight="600"
            >
              {item.label}
            </text>
            <text
              x="245"
              y={item.y + 11}
              textAnchor="middle"
              fill="var(--foreground)"
              fontSize="9"
            >
              {item.sub}
            </text>
          </g>
        ))}

        {/* Arrows right column */}
        <line
          x1="245"
          y1="50"
          x2="245"
          y2="82"
          stroke="var(--accent-purple)"
          strokeWidth="1.5"
          markerEnd="url(#rap)"
        />
        <line
          x1="245"
          y1="120"
          x2="245"
          y2="152"
          stroke="var(--primary)"
          strokeWidth="1.5"
          markerEnd="url(#ra)"
        />

        {/* Bridge DB → Hybrid */}
        <line
          x1="145"
          y1="165"
          x2="185"
          y2="112"
          stroke="var(--accent-green)"
          strokeWidth="1"
          strokeDasharray="4,3"
          markerEnd="url(#rag)"
        />

        {/* LLM */}
        <rect
          x="140"
          y="220"
          width="120"
          height="40"
          rx="8"
          fill="var(--muted)"
          stroke="var(--primary)"
          strokeWidth="2"
        />
        <text
          x="200"
          y="238"
          textAnchor="middle"
          fill="var(--primary)"
          fontSize="11"
          fontWeight="700"
        >
          LLM
        </text>
        <text
          x="200"
          y="252"
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
          y2="220"
          stroke="var(--accent-amber)"
          strokeWidth="1.5"
          markerEnd="url(#ray)"
        />

        {/* Markers */}
        <defs>
          <marker
            id="ra"
            markerWidth="7"
            markerHeight="7"
            refX="3.5"
            refY="3.5"
            orient="auto"
          >
            <path d="M0,0 L0,7 L7,3.5 z" fill="var(--primary)" />
          </marker>
          <marker
            id="rap"
            markerWidth="7"
            markerHeight="7"
            refX="3.5"
            refY="3.5"
            orient="auto"
          >
            <path d="M0,0 L0,7 L7,3.5 z" fill="var(--accent-purple)" />
          </marker>
          <marker
            id="rag"
            markerWidth="7"
            markerHeight="7"
            refX="3.5"
            refY="3.5"
            orient="auto"
          >
            <path d="M0,0 L0,7 L7,3.5 z" fill="var(--accent-green)" />
          </marker>
          <marker
            id="ray"
            markerWidth="7"
            markerHeight="7"
            refX="3.5"
            refY="3.5"
            orient="auto"
          >
            <path d="M0,0 L0,7 L7,3.5 z" fill="var(--accent-amber)" />
          </marker>
        </defs>
      </svg>
    </div>
  );
}

export default function RagFlowSection() {
  return (
    <section className="px-4 py-10 sm:px-6 sm:py-14 lg:px-8">
      <div className="mx-auto max-w-6xl">
        <div className="grid grid-cols-1 items-center gap-10 lg:grid-cols-2">
          <div>
            <h2 className="mb-6 text-2xl font-semibold text-foreground sm:text-3xl">
              {m.rag_heading()}
            </h2>
            <ul className="space-y-2.5">
              {[
                "PDF, DOCX, TXT, Markdown, código-fonte, planilhas",
                "Embeddings via Cohere (assimétrico: search_document / search_query)",
                "Hybrid RAG: dense (Cohere) + sparse (BM25) com RRF merge",
                "Multi-query: LLM gera N variantes da query para maior recall",
                "HyDE: documento hipotético quando score inicial é baixo",
                "Reranker Cohere para precisão máxima",
                "Citação da fonte em cada resposta",
              ].map((item, i) => (
                <li
                  key={i}
                  className="flex items-start gap-2.5 text-sm text-muted-foreground"
                >
                  <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
                  {item}
                </li>
              ))}
            </ul>
          </div>
          <RagDiagram />
        </div>
      </div>
    </section>
  );
}

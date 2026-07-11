import { m } from "#/paraglide/messages";
import {
  DiagramArc,
  DiagramArrowDefs,
  DiagramNodeView,
  DiagramPanelBg,
} from "#/components/landing/diagram-kit";
import type { DiagramNode } from "#/components/landing/diagram-kit";

const BULLETS = [
  m.rag_bullet_formats,
  m.rag_bullet_embeddings,
  m.rag_bullet_search,
  m.rag_bullet_rerank,
  m.rag_bullet_indexing,
  m.rag_bullet_curator,
  m.rag_bullet_citation,
];

/** Ícones de linha originais (traçado próprio) — um por tipo de nó do grafo. */
const ICONS = {
  document: (color: string) => (
    <g fill="none" stroke={color} strokeWidth="1.6" strokeLinejoin="round">
      <path d="M-7,-9 L3,-9 L7,-5 L7,9 L-7,9 Z" />
      <path d="M3,-9 L3,-5 L7,-5" />
      <line x1="-4" y1="-1" x2="4" y2="-1" strokeWidth="1.3" />
      <line x1="-4" y1="3" x2="4" y2="3" strokeWidth="1.3" />
    </g>
  ),
  chunking: (color: string) => (
    <g fill="none" stroke={color} strokeWidth="1.4">
      <rect x="-9" y="-4" width="5" height="8" rx="1" />
      <rect x="-2.5" y="-4" width="5" height="8" rx="1" />
      <rect x="4" y="-4" width="5" height="8" rx="1" />
    </g>
  ),
  lancedb: (color: string) => (
    <g fill="none" stroke={color} strokeWidth="1.4">
      <ellipse cx="0" cy="-5" rx="8" ry="3" />
      <path d="M-8,-5 L-8,5 A8,3 0 0,0 8,5 L8,-5" />
    </g>
  ),
  query: (color: string) => (
    <g>
      <rect
        x="-8"
        y="-7"
        width="16"
        height="11"
        rx="4"
        fill="none"
        stroke={color}
        strokeWidth="1.4"
      />
      <path
        d="M-2,4 L-4,9 L1,4"
        fill="none"
        stroke={color}
        strokeWidth="1.4"
        strokeLinejoin="round"
      />
      <text
        x="0"
        y="0.5"
        textAnchor="middle"
        fontSize="8"
        fontWeight="700"
        fill={color}
      >
        ?
      </text>
    </g>
  ),
  search: (color: string) => (
    <g fill="none" stroke={color}>
      <circle cx="-2" cy="-2" r="6" strokeWidth="1.5" />
      <line
        x1="3"
        y1="3"
        x2="8"
        y2="8"
        strokeWidth="1.7"
        strokeLinecap="round"
      />
    </g>
  ),
  reranker: (color: string) => (
    <path
      d="M-8,-7 L8,-7 L2,2 L2,8 L-2,8 L-2,2 Z"
      fill="none"
      stroke={color}
      strokeWidth="1.4"
      strokeLinejoin="round"
    />
  ),
  llm: (color: string) => (
    <path
      d="M0,-9 C1,-3 3,-1 9,0 C3,1 1,3 0,9 C-1,3 -3,1 -9,0 C-3,-1 -1,-3 0,-9 Z"
      fill={color}
      opacity="0.9"
    />
  ),
} as const;

function RagDiagram() {
  const documento: DiagramNode = {
    cx: 95,
    cy: 46,
    icon: ICONS.document,
    color: "primary",
    title: m.rag_diagram_document_title(),
    sub: m.rag_diagram_document_sub(),
  };
  const chunking: DiagramNode = {
    cx: 95,
    cy: 150,
    icon: ICONS.chunking,
    color: "cyan",
    title: m.rag_diagram_chunking_title(),
    sub: m.rag_diagram_chunking_sub(),
  };
  const lancedb: DiagramNode = {
    cx: 95,
    cy: 254,
    icon: ICONS.lancedb,
    color: "green",
    title: m.rag_diagram_lancedb_title(),
    sub: m.rag_diagram_lancedb_sub(),
  };
  const consulta: DiagramNode = {
    cx: 365,
    cy: 46,
    icon: ICONS.query,
    color: "purple",
    title: m.rag_diagram_query_title(),
    sub: m.rag_diagram_query_sub(),
  };
  const busca: DiagramNode = {
    cx: 365,
    cy: 150,
    icon: ICONS.search,
    color: "pink",
    title: m.rag_diagram_search_title(),
    sub: m.rag_diagram_search_sub(),
  };
  const reranker: DiagramNode = {
    cx: 365,
    cy: 254,
    icon: ICONS.reranker,
    color: "amber",
    title: m.rag_diagram_reranker_title(),
    sub: m.rag_diagram_reranker_sub(),
  };
  const llm: DiagramNode = {
    cx: 230,
    cy: 316,
    r: 26,
    icon: ICONS.llm,
    color: "red",
    title: m.rag_diagram_llm_title(),
    sub: m.rag_diagram_llm_sub(),
  };

  return (
    <div
      className="flex h-full items-center justify-center overflow-hidden rounded-2xl border border-border p-6"
      aria-hidden
    >
      <svg
        viewBox="0 0 460 395"
        className="w-full"
        style={{ fontFamily: "inherit" }}
      >
        <DiagramArrowDefs />
        <DiagramPanelBg width={460} height={395} />

        <DiagramArc from={documento} to={chunking} colorKey="primary" />
        <DiagramArc from={chunking} to={lancedb} colorKey="cyan" />
        <DiagramArc from={consulta} to={busca} colorKey="purple" />
        <DiagramArc from={busca} to={reranker} colorKey="pink" />
        <DiagramArc from={lancedb} to={busca} colorKey="green" dashed />
        <DiagramArc from={lancedb} to={llm} colorKey="green" />
        <DiagramArc from={reranker} to={llm} colorKey="amber" />

        {[documento, chunking, lancedb, consulta, busca, reranker, llm].map(
          (node) => (
            <DiagramNodeView key={node.title} node={node} />
          ),
        )}
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

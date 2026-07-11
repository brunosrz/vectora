import { m } from "#/paraglide/messages";
import {
  DiagramArc,
  DiagramArrowDefs,
  DiagramNodeView,
  DiagramPanelBg,
} from "#/components/landing/diagram-kit";
import type { DiagramNode } from "#/components/landing/diagram-kit";

/** Ícones de linha originais (traçado próprio) — um por agente do grafo. */
const ICONS = {
  user: (color: string) => (
    <g fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round">
      <circle cx="0" cy="-4" r="3.2" />
      <path d="M-6,7 C-6,1 6,1 6,7" />
    </g>
  ),
  hub: (color: string) => (
    <g stroke={color} fill="none">
      <circle cx="0" cy="0" r="2.6" fill={color} />
      <circle cx="0" cy="-10" r="2.4" strokeWidth="1.5" />
      <circle cx="9" cy="6" r="2.4" strokeWidth="1.5" />
      <circle cx="-9" cy="6" r="2.4" strokeWidth="1.5" />
      <line x1="0" y1="-2.4" x2="0" y2="-7.6" strokeWidth="1.3" />
      <line x1="1.9" y1="1.6" x2="7.4" y2="4.6" strokeWidth="1.3" />
      <line x1="-1.9" y1="1.6" x2="-7.4" y2="4.6" strokeWidth="1.3" />
    </g>
  ),
  code: (color: string) => (
    <g
      fill="none"
      stroke={color}
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M-3,-7 L-8,0 L-3,7" />
      <path d="M3,-7 L8,0 L3,7" />
    </g>
  ),
  globe: (color: string) => (
    <g fill="none" stroke={color} strokeWidth="1.3">
      <circle cx="0" cy="0" r="7.5" />
      <ellipse cx="0" cy="0" rx="3.2" ry="7.5" />
      <line x1="-7.5" y1="0" x2="7.5" y2="0" />
    </g>
  ),
} as const;

/** Retângulo opaco atrás de um texto solto (não preso a um nó) — mesma
 * técnica do diagram-kit, aqui só pro label "Resposta" perto da seta. */
function FloatingLabel({
  cx,
  cy,
  text,
}: {
  cx: number;
  cy: number;
  text: string;
}) {
  const w = text.length * 11 * 0.62 + 6;
  return (
    <g>
      <rect
        x={cx - w / 2}
        y={cy - 8}
        width={w}
        height={13}
        fill="var(--card)"
      />
      <text
        x={cx}
        y={cy + 3}
        textAnchor="middle"
        fill="var(--muted-foreground)"
        fontSize="11"
        fontWeight="600"
      >
        {text}
      </text>
    </g>
  );
}

function AgenticDiagram() {
  const usuario: DiagramNode = {
    cx: 230,
    cy: 34,
    r: 16,
    icon: ICONS.user,
    color: "muted",
    title: m.agentic_diagram_user(),
    sub: "",
  };
  const orchestrator: DiagramNode = {
    cx: 230,
    cy: 122,
    r: 24,
    icon: ICONS.hub,
    color: "primary",
    title: m.agentic_diagram_orchestrator_title(),
    sub: m.agentic_diagram_orchestrator_sub(),
  };
  const coder: DiagramNode = {
    cx: 130,
    cy: 236,
    r: 19,
    icon: ICONS.code,
    color: "cyan",
    title: m.agentic_diagram_coder_title(),
    sub: m.agentic_diagram_coder_sub(),
  };
  const search: DiagramNode = {
    cx: 330,
    cy: 236,
    r: 19,
    icon: ICONS.globe,
    color: "purple",
    title: m.agentic_diagram_search_title(),
    sub: m.agentic_diagram_search_sub(),
  };

  return (
    <div
      className="flex h-full items-center justify-center overflow-hidden rounded-2xl border border-border p-6"
      aria-hidden
    >
      <svg
        viewBox="0 0 460 300"
        className="w-full"
        style={{ fontFamily: "inherit" }}
      >
        <DiagramArrowDefs />
        <DiagramPanelBg width={460} height={300} />

        {/* Usuário ⇄ Orchestrator — UMA linha só, seta nos dois lados (mão
         * dupla: pedido desce, resposta sobe). Duas curvas separadas aqui
         * ficavam redundantes/confusas numa distância tão curta. */}
        <DiagramArc
          from={usuario}
          to={orchestrator}
          colorKey="primary"
          bow={0}
          bidirectional
        />
        <FloatingLabel cx={300} cy={78} text={m.agentic_diagram_response()} />

        <DiagramArc from={orchestrator} to={coder} colorKey="cyan" />
        <DiagramArc from={orchestrator} to={search} colorKey="purple" />

        {[usuario, orchestrator, coder, search].map((node) => (
          <DiagramNodeView key={node.title} node={node} />
        ))}
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
    <section className="px-4 py-[23px] sm:px-6 lg:px-8">
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

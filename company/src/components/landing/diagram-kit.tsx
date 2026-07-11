import type { ReactNode } from "react";

/** Paleta compartilhada dos diagramas SVG da landing — uma cor exclusiva por
 * nó, nunca repetida dentro de um mesmo grafo. Chave usada tanto pro
 * `<marker>` da seta quanto pro estilo do nó. */
export const DIAGRAM_COLORS = {
  primary: "var(--primary)",
  cyan: "var(--accent-cyan)",
  green: "var(--accent-green)",
  purple: "var(--accent-purple)",
  pink: "var(--accent-pink)",
  amber: "var(--accent-amber)",
  red: "var(--accent-red)",
  muted: "var(--muted-foreground)",
} as const;

export type ColorKey = keyof typeof DIAGRAM_COLORS;

export interface DiagramNode {
  cx: number;
  cy: number;
  r?: number;
  color: ColorKey;
  title: string;
  sub: string;
  /** Ícone de linha original — recebe a cor já resolvida do nó. */
  icon: (color: string) => ReactNode;
}

/** Quebra a legenda em 2 linhas se passar de ~22 caracteres — sem isso o
 * texto solto (sem caixa) pode encostar no nó vizinho em traduções longas. */
export function wrapSub(sub: string): string[] {
  if (sub.length <= 22) return [sub];
  const mid = Math.floor(sub.length / 2);
  let splitAt = sub.lastIndexOf(" ", mid);
  if (splitAt <= 0) splitAt = sub.indexOf(" ", mid);
  if (splitAt <= 0) return [sub];
  return [sub.slice(0, splitAt), sub.slice(splitAt + 1)];
}

/** Largura aproximada de uma linha de texto (sem medir layout — chute por
 * caractere é suficiente pro retângulo de fundo só precisar cobrir, não
 * encaixar pixel-perfeito). */
function approxWidth(text: string, fontSize: number): number {
  return text.length * fontSize * 0.62;
}

/** Retângulo opaco atrás de uma linha de texto — sem isso, as setas que
 * cruzam por baixo do label ficam visíveis entre as letras e parecem
 * "passar na frente" do texto em vez de atrás. */
function LabelBackground({
  cx,
  cy,
  text,
  fontSize,
}: {
  cx: number;
  cy: number;
  text: string;
  fontSize: number;
}) {
  const w = approxWidth(text, fontSize) + 6;
  const h = fontSize + 4;
  return (
    <rect
      x={cx - w / 2}
      y={cy - h / 2}
      width={w}
      height={h}
      fill="var(--card)"
    />
  );
}

export function DiagramNodeView({ node }: { node: DiagramNode }) {
  const r = node.r ?? 22;
  const color = DIAGRAM_COLORS[node.color];
  const subLines = wrapSub(node.sub);
  const titleY = node.cy + r + 14;
  const subLineHeight = 11;
  const firstSubY = node.cy + r + 26;

  return (
    <g>
      {/* Fundo opaco atrás de cada linha — desenhado ANTES do nó (que vem a
       * seguir), então cobre qualquer seta que passe por baixo do label. */}
      <LabelBackground
        cx={node.cx}
        cy={titleY - 4}
        text={node.title}
        fontSize={11}
      />
      {subLines.map((line, i) => (
        <LabelBackground
          key={i}
          cx={node.cx}
          cy={firstSubY - 3 + i * subLineHeight}
          text={line}
          fontSize={9}
        />
      ))}

      <circle
        cx={node.cx}
        cy={node.cy}
        r={r}
        fill={`color-mix(in srgb, ${color} 14%, var(--node-surface))`}
        stroke={color}
        strokeWidth="1.8"
      />
      <g transform={`translate(${node.cx}, ${node.cy})`}>{node.icon(color)}</g>
      <text
        x={node.cx}
        y={titleY}
        textAnchor="middle"
        fill={color}
        fontSize="11"
        fontWeight="700"
      >
        {node.title}
      </text>
      <text
        x={node.cx}
        y={firstSubY}
        textAnchor="middle"
        fill="var(--muted-foreground)"
        fontSize="9"
      >
        {subLines.map((line, i) => (
          <tspan key={i} x={node.cx} dy={i === 0 ? 0 : subLineHeight}>
            {line}
          </tspan>
        ))}
      </text>
    </g>
  );
}

/** Seta curva entre dois nós — estilo arco suave (raio do nó descontado nas
 * pontas pra não sobrepor os círculos). A ponta usa um `<marker>` próprio da
 * cor de origem (`colorKey`), pra não depender de um marker azul fixo. */
export function DiagramArc({
  from,
  to,
  colorKey,
  dashed,
  bow = 18,
  bidirectional,
}: {
  from: DiagramNode;
  to: DiagramNode;
  colorKey: ColorKey;
  dashed?: boolean;
  bow?: number;
  /** Uma linha só com seta nas duas pontas — pra relações de mão-dupla (ex.:
   * usuário ⇄ orquestrador), em vez de duas curvas separadas que se
   * confundem visualmente numa distância curta. */
  bidirectional?: boolean;
}) {
  const fr = from.r ?? 22;
  const tr = to.r ?? 22;
  const dx = to.cx - from.cx;
  const dy = to.cy - from.cy;
  const len = Math.hypot(dx, dy) || 1;
  const ux = dx / len;
  const uy = dy / len;
  const startPad = bidirectional ? fr + 6 : fr;
  const x1 = from.cx + ux * startPad;
  const y1 = from.cy + uy * startPad;
  const x2 = to.cx - ux * (tr + 6);
  const y2 = to.cy - uy * (tr + 6);
  const mx = (x1 + x2) / 2 - uy * bow;
  const my = (y1 + y2) / 2 + ux * bow;
  return (
    <path
      d={`M${x1},${y1} Q${mx},${my} ${x2},${y2}`}
      fill="none"
      stroke={DIAGRAM_COLORS[colorKey]}
      strokeWidth={dashed ? 1.3 : 1.7}
      strokeDasharray={dashed ? "4,3" : undefined}
      markerStart={bidirectional ? `url(#rag-arrow-${colorKey})` : undefined}
      markerEnd={`url(#rag-arrow-${colorKey})`}
    />
  );
}

/** `<defs>` com um marker de seta por cor da paleta — importar uma vez por
 * diagrama, dentro do próprio `<svg>`. */
export function DiagramArrowDefs() {
  return (
    <defs>
      {(Object.keys(DIAGRAM_COLORS) as ColorKey[]).map((key) => (
        <marker
          key={key}
          id={`rag-arrow-${key}`}
          viewBox="0 0 8 8"
          refX="6"
          refY="4"
          markerWidth="6"
          markerHeight="6"
          orient="auto-start-reverse"
        >
          <path d="M0,0 L8,4 L0,8 Z" fill={DIAGRAM_COLORS[key]} />
        </marker>
      ))}
    </defs>
  );
}

/** Fundo opaco do painel inteiro — os retângulos atrás de cada label usam a
 * MESMA cor sólida, então a costura fica invisível e as setas somem de
 * verdade atrás do texto, não só ficam por baixo em z-index sobre um fundo
 * translúcido. */
export function DiagramPanelBg({
  width,
  height,
}: {
  width: number;
  height: number;
}) {
  return <rect width={width} height={height} fill="var(--card)" />;
}

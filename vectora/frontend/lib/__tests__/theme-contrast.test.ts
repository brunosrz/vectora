/**
 * Regressão de legibilidade do tema claro ("Min Light"): garante que os tokens
 * de texto têm contraste WCAG suficiente sobre o background branco. Parseia o
 * styles.css real para travar o requisito ("tema claro pouco legível").
 */

import { readFileSync } from "node:fs";
import path from "node:path";

import { describe, it, expect } from "vitest";

const css = readFileSync(
  path.resolve(process.cwd(), "src/styles.css"),
  "utf-8",
);

/** Extrai o valor hex de um token dentro do bloco `.light`. */
function lightToken(name: string): string {
  // Começa na REGRA `.light {` (não no comentário que cita ".light"); limita ao
  // bloco até o `}` de fechamento para não casar tokens de outros temas.
  const start = css.indexOf(".light {");
  const block = css.slice(start, css.indexOf("}", start));
  const m = block.match(new RegExp(`--${name}:\\s*(#[0-9a-fA-F]{6})`));
  if (!m) throw new Error(`token --${name} não encontrado no bloco .light`);
  return m[1];
}

function luminance(hex: string): number {
  const ch = [1, 3, 5].map((i) => {
    const v = parseInt(hex.slice(i, i + 2), 16) / 255;
    return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * ch[0] + 0.7152 * ch[1] + 0.0722 * ch[2];
}

function contrast(fg: string, bg: string): number {
  const l1 = luminance(fg);
  const l2 = luminance(bg);
  const [hi, lo] = l1 > l2 ? [l1, l2] : [l2, l1];
  return (hi + 0.05) / (lo + 0.05);
}

describe("tema claro — legibilidade (Min Light)", () => {
  it("background do tema claro é branco", () => {
    expect(lightToken("background").toLowerCase()).toBe("#ffffff");
  });

  it("foreground tem contraste AAA (>=7) sobre o background", () => {
    const c = contrast(lightToken("foreground"), lightToken("background"));
    expect(c).toBeGreaterThanOrEqual(7);
  });

  it("muted-foreground passa o mínimo AA (>=4.5)", () => {
    const c = contrast(
      lightToken("muted-foreground"),
      lightToken("background"),
    );
    expect(c).toBeGreaterThanOrEqual(4.5);
  });

  it("muted-foreground foi reforçado para >=6 (legibilidade)", () => {
    const c = contrast(
      lightToken("muted-foreground"),
      lightToken("background"),
    );
    expect(c).toBeGreaterThanOrEqual(6);
  });

  it("card-foreground tem contraste AAA sobre o card", () => {
    const c = contrast(lightToken("card-foreground"), lightToken("card"));
    expect(c).toBeGreaterThanOrEqual(7);
  });

  it("destructive-foreground é legível sobre destructive", () => {
    const c = contrast(
      lightToken("destructive-foreground"),
      lightToken("destructive"),
    );
    expect(c).toBeGreaterThanOrEqual(4.5);
  });

  it("primary-foreground é legível sobre primary (CTA)", () => {
    const c = contrast(lightToken("primary-foreground"), lightToken("primary"));
    expect(c).toBeGreaterThanOrEqual(7);
  });
});

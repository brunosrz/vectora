/**
 * Tests para stripMarkdownEnvelope: desempacota o envelope ``````markdown
 * (completo, parcial/streaming, sem envelope) preservando fences internos.
 */

import { describe, expect, it } from "vitest";
import { stripMarkdownEnvelope } from "@/lib/utils/string/markdown-envelope";

const FENCE = "``````";

describe("stripMarkdownEnvelope", () => {
  it("desempacota o envelope completo", () => {
    const input = `${FENCE}markdown\n# Olá\n${FENCE}`;
    expect(stripMarkdownEnvelope(input)).toBe("# Olá");
  });

  it("preserva blocos de código triplos internos", () => {
    const body = '# T\n```python\nprint("x")\n```';
    const input = `${FENCE}markdown\n${body}\n${FENCE}`;
    expect(stripMarkdownEnvelope(input)).toBe(body);
  });

  it("remove só a abertura quando o stream ainda está chegando", () => {
    const input = `${FENCE}markdown\n# parcial`;
    expect(stripMarkdownEnvelope(input)).toBe("# parcial");
  });

  it("remove o fechamento parcial no fim do stream", () => {
    const input = `${FENCE}markdown\n# corpo\n${FENCE}`;
    expect(stripMarkdownEnvelope(input)).toBe("# corpo");
  });

  it("tolera CRLF e espaços ao redor do fence", () => {
    const input = `  ${FENCE}markdown\r\n# win\r\n${FENCE}  `;
    expect(stripMarkdownEnvelope(input)).toBe("# win");
  });

  it("retorna o texto inalterado quando não há envelope", () => {
    expect(stripMarkdownEnvelope("texto plano")).toBe("texto plano");
  });

  it("retorna inalterado para string vazia", () => {
    expect(stripMarkdownEnvelope("")).toBe("");
  });
});

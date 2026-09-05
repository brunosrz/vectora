import type { BaseThemeColors } from "@/lib/theme/presets";

interface VscodeColorTheme {
  colors?: Record<string, string>;
}

/** Cores VS Code que cada campo de `BaseThemeColors` lê, em ordem de
 * preferência (o primeiro presente na paleta vence). */
const FIELD_SOURCES: Record<keyof BaseThemeColors, string[]> = {
  background: ["editor.background"],
  foreground: ["editor.foreground", "foreground"],
  card: ["editorWidget.background", "sideBar.background"],
  border: ["editorWidget.border", "panel.border", "editorGroup.border"],
  primary: ["button.background", "focusBorder", "textLink.foreground"],
  accent: ["list.hoverBackground", "editor.selectionBackground"],
  muted: ["input.background", "editorWidget.background"],
  sidebar: ["sideBar.background", "activityBar.background"],
  userBubble: ["button.background", "focusBorder"],
};

function relativeLuminance(hex: string): number {
  const m = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})/i.exec(hex.trim());
  if (!m) return 1;
  const [r, g, b] = [m[1]!, m[2]!, m[3]!].map((h) => parseInt(h, 16) / 255);
  return 0.2126 * r! + 0.7152 * g! + 0.0722 * b!;
}

function firstDefined(
  colors: Record<string, string>,
  keys: string[],
  fallback: string,
): string {
  for (const key of keys) {
    const v = colors[key];
    if (v) return v;
  }
  return fallback;
}

const HEX_RE = /^#?([a-f\d]{3,4}|[a-f\d]{6}|[a-f\d]{8})$/i;

/** Normaliza um valor de cor do VS Code pro formato `#rrggbb` que
 * `BaseThemeColors` espera: expande as formas curtas (`#rgb`/`#rgba`) e
 * descarta o canal alfa das formas longas (`#rrggbbaa`). Temas reais usam
 * cores com alfa com frequência (ex. overlays semi-transparentes) — sem
 * essa normalização, um valor de 8 dígitos vaza pro campo, quebra
 * `relativeLuminance`/`contrastFg` (que só casam hex de 6 dígitos) e
 * produz texto escuro sobre fundo escuro em `--accent-foreground`.
 * Valores que não são hex (nomes de cor CSS, `rgba(...)`, `transparent`)
 * passam direto — não há como normalizá-los pro mesmo formato sem uma
 * lib de cor inteira, e são raros nas chaves que `FIELD_SOURCES` lê. */
function normalizeHex(value: string): string {
  const m = HEX_RE.exec(value.trim());
  if (!m) return value;
  let digits = m[1]!.toLowerCase();
  if (digits.length === 3 || digits.length === 4) {
    digits = digits
      .split("")
      .map((c) => c + c)
      .join("");
  }
  return `#${digits.slice(0, 6)}`;
}

/**
 * Converte um tema de cores do VS Code (`colors` de um arquivo
 * `contributes.themes[].path`) nos 9 campos de `BaseThemeColors` — mapeia
 * por prioridade de chave (ver `FIELD_SOURCES`) já que um tema VS Code tem
 * dezenas de chaves e a Vectora só precisa das 9 mais visíveis.
 *
 * Lança se o JSON não tiver nem `editor.background` nem `editor.foreground`
 * — sem essas duas não dá pra derivar um tema minimamente coerente.
 */
export function convertVscodeColorTheme(json: unknown): BaseThemeColors {
  const parsed = json as VscodeColorTheme;
  const colors = parsed?.colors ?? {};
  const background = colors["editor.background"];
  const foreground = colors["editor.foreground"];
  if (!background || !foreground) {
    throw new Error(
      "Tema VS Code sem editor.background/editor.foreground — não é possível converter.",
    );
  }

  const result = {} as BaseThemeColors;
  for (const key of Object.keys(FIELD_SOURCES) as (keyof BaseThemeColors)[]) {
    const fallback = key === "background" ? background : foreground;
    result[key] = normalizeHex(
      firstDefined(colors, FIELD_SOURCES[key], fallback),
    );
  }
  return result;
}

/** `true` se o tema convertido é claro (fundo com luminância alta) —
 * usado só para escolher o sufixo do id/label instalado, não afeta as
 * cores em si. */
export function isLightTheme(base: BaseThemeColors): boolean {
  return relativeLuminance(base.background) > 0.5;
}

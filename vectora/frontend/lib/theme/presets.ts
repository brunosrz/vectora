/**
 * presets.ts — paletas de tema prontas (inspiradas em temas populares do
 * VS Code, todos open-source) + utilitários para aplicar/derivar tokens
 * de cor como CSS custom properties em `document.documentElement`.
 *
 * Cada preset define só as cores "base" (as mais visíveis); as demais
 * variáveis do design system (`--muted-foreground`, `--ring` etc.) são
 * derivadas via `buildThemeTokens()` usando `color-mix()` e contraste
 * automático — evita ter que listar 19 cores por preset.
 */

export interface BaseThemeColors {
  background: string;
  foreground: string;
  card: string;
  border: string;
  primary: string;
  accent: string;
  muted: string;
  sidebar: string;
}

export interface ThemePresetDef {
  id: string;
  label: string;
  colors: BaseThemeColors;
}

/** Variáveis CSS publicadas em `:root` / `.light` (ver styles.css). */
const TOKEN_VAR_NAMES = [
  "--background",
  "--foreground",
  "--card",
  "--card-foreground",
  "--popover",
  "--popover-foreground",
  "--muted",
  "--muted-foreground",
  "--secondary",
  "--secondary-foreground",
  "--accent",
  "--accent-foreground",
  "--border",
  "--input",
  "--primary",
  "--primary-foreground",
  "--ring",
  "--sidebar",
] as const;

/** Presets baseados nos temas originais do VS Code (paletas open-source). */
export const THEME_PRESETS: ThemePresetDef[] = [
  {
    id: "min-dark",
    label: "Min Dark",
    colors: {
      background: "#1f1f1f",
      foreground: "#d4d4d4",
      card: "#1a1a1a",
      border: "#2a2a2a",
      primary: "#d4d4d4",
      accent: "#2a2a2a",
      muted: "#262626",
      sidebar: "#181818",
    },
  },
  {
    id: "min-light",
    label: "Min Light",
    colors: {
      background: "#ffffff",
      foreground: "#2b2b2b",
      card: "#f6f6f6",
      border: "#d8d8d8",
      primary: "#2b2b2b",
      accent: "#eeeeee",
      muted: "#f0f0f0",
      sidebar: "#f3f3f3",
    },
  },
  {
    id: "github-dark",
    label: "GitHub Dark",
    colors: {
      background: "#0d1117",
      foreground: "#e6edf3",
      card: "#161b22",
      border: "#30363d",
      primary: "#58a6ff",
      accent: "#21262d",
      muted: "#21262d",
      sidebar: "#010409",
    },
  },
  {
    id: "github-light",
    label: "GitHub Light",
    colors: {
      background: "#ffffff",
      foreground: "#24292f",
      card: "#f6f8fa",
      border: "#d0d7de",
      primary: "#0969da",
      accent: "#eaeef2",
      muted: "#f6f8fa",
      sidebar: "#f6f8fa",
    },
  },
];

/** Cor de fallback para customização — espelha o tema escuro padrão (Min Dark). */
export const DEFAULT_CUSTOM_COLORS: BaseThemeColors = {
  background: "#1f1f1f",
  foreground: "#d4d4d4",
  card: "#1a1a1a",
  border: "#2a2a2a",
  primary: "#79b8ff",
  accent: "#2a2a2a",
  muted: "#262626",
  sidebar: "#181818",
};

/** Luminância relativa aproximada (sRGB) — usada para escolher fg de contraste. */
function relativeLuminance(hex: string): number {
  const m = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex.trim());
  if (!m) return 1;
  const [r, g, b] = [m[1]!, m[2]!, m[3]!].map((h) => parseInt(h, 16) / 255);
  return 0.2126 * r! + 0.7152 * g! + 0.0722 * b!;
}

/** Retorna preto ou branco — o que tiver mais contraste contra `hex`. */
function contrastFg(hex: string): string {
  return relativeLuminance(hex) > 0.5 ? "#0a0a0a" : "#fafafa";
}

/**
 * Expande as 7 cores-base de um preset/customização para o conjunto completo
 * de tokens do design system, retornando um mapa `--var → valor` pronto
 * para `style.setProperty`.
 */
export function buildThemeTokens(
  base: BaseThemeColors,
): Record<string, string> {
  return {
    "--background": base.background,
    "--foreground": base.foreground,
    "--card": base.card,
    "--card-foreground": base.foreground,
    "--popover": base.card,
    "--popover-foreground": base.foreground,
    "--muted": base.muted,
    "--muted-foreground": `color-mix(in srgb, ${base.foreground} 65%, ${base.background})`,
    "--secondary": base.muted,
    "--secondary-foreground": base.foreground,
    "--accent": base.accent,
    "--accent-foreground": contrastFg(base.accent),
    "--border": base.border,
    "--input": base.border,
    "--primary": base.primary,
    "--primary-foreground": contrastFg(base.primary),
    "--ring": base.primary,
    "--sidebar": base.sidebar,
  };
}

/**
 * Aplica (ou remove, se `tokens` for `null`) os overrides de cor em
 * `document.documentElement.style`. `null` restaura os valores padrão
 * de `:root` / `.light` definidos em styles.css.
 */
export function applyThemeTokens(tokens: Record<string, string> | null): void {
  if (typeof document === "undefined") return;
  const root = document.documentElement;
  if (!tokens) {
    for (const name of TOKEN_VAR_NAMES) root.style.removeProperty(name);
    return;
  }
  for (const name of TOKEN_VAR_NAMES) {
    const value = tokens[name];
    if (value) root.style.setProperty(name, value);
    else root.style.removeProperty(name);
  }
}

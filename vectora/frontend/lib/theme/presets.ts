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
] as const;

/** Presets inspirados em temas conhecidos do VS Code (paletas open-source). */
export const THEME_PRESETS: ThemePresetDef[] = [
  {
    id: "dracula",
    label: "Dracula",
    colors: {
      background: "#282a36",
      foreground: "#f8f8f2",
      card: "#21222c",
      border: "#44475a",
      primary: "#bd93f9",
      accent: "#ff79c6",
      muted: "#343746",
    },
  },
  {
    id: "monokai",
    label: "Monokai",
    colors: {
      background: "#272822",
      foreground: "#f8f8f2",
      card: "#1e1f1c",
      border: "#49483e",
      primary: "#a6e22e",
      accent: "#66d9ef",
      muted: "#3e3d32",
    },
  },
  {
    id: "nord",
    label: "Nord",
    colors: {
      background: "#2e3440",
      foreground: "#d8dee9",
      card: "#3b4252",
      border: "#4c566a",
      primary: "#88c0d0",
      accent: "#81a1c1",
      muted: "#434c5e",
    },
  },
  {
    id: "one-dark",
    label: "One Dark Pro",
    colors: {
      background: "#282c34",
      foreground: "#abb2bf",
      card: "#21252b",
      border: "#3a3f4b",
      primary: "#61afef",
      accent: "#c678dd",
      muted: "#2c313a",
    },
  },
  {
    id: "solarized-light",
    label: "Solarized Light",
    colors: {
      background: "#fdf6e3",
      foreground: "#657b83",
      card: "#eee8d5",
      border: "#d3cbb7",
      primary: "#268bd2",
      accent: "#2aa198",
      muted: "#eee8d5",
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
      accent: "#8250df",
      muted: "#f6f8fa",
    },
  },
  {
    id: "github-dark",
    label: "GitHub Dark",
    colors: {
      background: "#0d1117",
      foreground: "#c9d1d9",
      card: "#161b22",
      border: "#30363d",
      primary: "#58a6ff",
      accent: "#bc8cff",
      muted: "#161b22",
    },
  },
  {
    id: "min-dark",
    label: "Min Dark",
    colors: {
      background: "#1e1e1e",
      foreground: "#d4d4d4",
      card: "#252526",
      border: "#2d2d2d",
      primary: "#569cd6",
      // `accent` é o token de hover/superfície (shadcn `hover:bg-accent`), não a
      // cor de destaque de sintaxe — mantém o hover neutro como o tema base
      // (`#2a2a2a`); o teal do VS Code (#4ec9b0) deixava todos os hovers verdes.
      accent: "#2a2a2a",
      muted: "#2a2a2a",
    },
  },
  {
    id: "min-light",
    label: "Min Light",
    colors: {
      background: "#ffffff",
      foreground: "#3b3b3b",
      card: "#f5f5f5",
      border: "#e5e5e5",
      primary: "#1a73e8",
      // Hover/superfície neutro como o tema base claro (não a cor de destaque).
      accent: "#eeeeee",
      muted: "#f0f0f0",
    },
  },
  {
    id: "solarized-dark",
    label: "Solarized Dark",
    colors: {
      background: "#002b36",
      foreground: "#839496",
      card: "#073642",
      border: "#586e75",
      primary: "#268bd2",
      accent: "#2aa198",
      muted: "#073642",
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

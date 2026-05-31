/**
 * Helpers de formatação e classificação para o medidor de uso (K.2.2).
 */

/** Formata número de tokens com sufixo k/M (1234 → "1.2k"). */
export function formatTokens(n: number): string {
  if (!Number.isFinite(n) || n <= 0) return "0";
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}k`;
  return `${n}`;
}

/**
 * Formata janela de reset em "Xh", "Ym" ou "Zs" — escolhe a maior unidade
 * inteira disponível para evitar valores longos como "17400s".
 */
export function formatResetIn(seconds: number): string {
  const s = Math.max(0, Math.round(seconds));
  if (s >= 3600) return `${Math.round(s / 3600)}h`;
  if (s >= 60) return `${Math.round(s / 60)}m`;
  return `${s}s`;
}

/**
 * Classifica uma porcentagem em níveis semafóricos. As barras do popover
 * usam essas classes para refletir a saúde do consumo.
 */
export function usageLevel(pct: number): "ok" | "warn" | "danger" {
  if (pct >= 85) return "danger";
  if (pct >= 60) return "warn";
  return "ok";
}

/** Cor de fundo Tailwind para a barra por nível. */
export function usageBarColor(level: "ok" | "warn" | "danger"): string {
  if (level === "danger") return "bg-red-500";
  if (level === "warn") return "bg-amber-500";
  return "bg-emerald-500";
}

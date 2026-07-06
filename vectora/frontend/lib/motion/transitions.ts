/**
 * Timing/easing compartilhado do motion (framer-motion) — mesma constante
 * usada pelo workbench (troca de aba) e pela sidebar (collapse/expand,
 * grupos de workspace), pra manter o "feel" consistente entre as duas
 * áreas em vez de cada componente inventar o próprio timing.
 */
export const PANEL_TRANSITION = {
  duration: 0.14,
  ease: [0.4, 0, 0.2, 1] as const,
};

import { useEffect, useState } from "react";

/**
 * Reage a uma media query via `matchMedia`, com valor inicial síncrono
 * (evita flash — o listener só cobre mudanças pós-mount, ex: resize da
 * janela ou rotação do dispositivo).
 */
export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(
    () => typeof window !== "undefined" && window.matchMedia(query).matches,
  );

  useEffect(() => {
    const mql = window.matchMedia(query);
    setMatches(mql.matches);
    const handler = (e: MediaQueryListEvent) => setMatches(e.matches);
    mql.addEventListener("change", handler);
    return () => mql.removeEventListener("change", handler);
  }, [query]);

  return matches;
}

/** Breakpoint `md` do Tailwind (768px) — abaixo dele, layouts multi-painel
 * colapsam para um único painel visível por vez. */
export const MD_BREAKPOINT_QUERY = "(max-width: 767px)";

export function useIsNarrowViewport(): boolean {
  return useMediaQuery(MD_BREAKPOINT_QUERY);
}

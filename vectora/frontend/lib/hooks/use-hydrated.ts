"use client";

/**
 * useHydrated — true após o primeiro render no client.
 *
 * Usado para gatear leituras de stores Zustand com `persist` (que partem
 * do default no SSR e mudam após a hidratação do localStorage). Renderizar
 * o valor real só depois de hidratar evita "Hydration failed because the
 * server rendered HTML didn't match the client".
 *
 * Padrão típico:
 *
 *   const hydrated = useHydrated();
 *   const showPanel = useStore((s) => s.isOpen("...")) && hydrated;
 *
 * Mais simples que `persist.skipHydration` + rehydrate manual, e evita
 * o flash de conteúdo "errado" do default.
 */

import { useEffect, useState } from "react";

export function useHydrated(): boolean {
  const [hydrated, setHydrated] = useState(false);
  useEffect(() => {
    setHydrated(true);
  }, []);
  return hydrated;
}

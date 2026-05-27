"use client";

/**
 * ThemeProvider — Bloco L3
 *
 * Envolve o app com o ThemeProvider do next-themes.
 * Lê o tema do settings-store e sincroniza com next-themes ao montar.
 */

import { ThemeProvider as NextThemesProvider } from "next-themes";
import { useEffect } from "react";
import { useSettingsStore } from "@/lib/stores/settings-store";

interface ThemeProviderProps {
  children: React.ReactNode;
}

/**
 * Hook interno: sincroniza o tema salvo no Zustand com next-themes.
 * Necessário porque next-themes lê o tema do seu próprio localStorage,
 * enquanto o Vectora persiste no settings-store com prefixo por usuário.
 */
function ThemeSync() {
  const theme = useSettingsStore((s) => s.theme);
  return null; // Efeito via useSettingsStore subscription
}

export function ThemeProvider({ children }: ThemeProviderProps) {
  return (
    <NextThemesProvider
      attribute="class"
      defaultTheme="system"
      enableSystem
      disableTransitionOnChange
    >
      <ThemeSync />
      {children}
    </NextThemesProvider>
  );
}

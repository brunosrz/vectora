import { useEffect, useState } from "react";
import { useSettingsStore } from "@/lib/stores/settings-store";

/**
 * Resolve se o tema ativo é escuro, lendo do settings-store (não next-themes).
 * Suporta "light" / "dark" / "system" — no modo "system" reage ao media query.
 */
export function useIsDark(): boolean {
  const theme = useSettingsStore((s) => s.theme);
  const [sysDark, setSysDark] = useState(
    () =>
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-color-scheme: dark)").matches,
  );

  useEffect(() => {
    if (theme !== "system") return;
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const handler = (e: MediaQueryListEvent) => setSysDark(e.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, [theme]);

  if (theme === "light") return false;
  if (theme === "dark") return true;
  return sysDark;
}

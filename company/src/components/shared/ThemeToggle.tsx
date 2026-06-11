import { useEffect, useState } from "react";
import { Moon, Sun } from "lucide-react";
import { m } from "#/paraglide/messages";
import {
  applyTheme,
  getStoredTheme,
  resolveTheme,
  setTheme,
  watchSystemTheme,
} from "#/lib/theme";

/** Botão sol/lua que alterna entre os modos claro e escuro (paleta Min). */
export default function ThemeToggle() {
  // Estado efetivo (light/dark) — inicia null no SSR para evitar mismatch.
  const [mode, setMode] = useState<"light" | "dark" | null>(null);

  useEffect(() => {
    applyTheme(getStoredTheme());
    setMode(resolveTheme(getStoredTheme()));
    return watchSystemTheme();
  }, []);

  const toggle = () => {
    const next = mode === "dark" ? "light" : "dark";
    setTheme(next);
    setMode(next);
  };

  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={mode === "dark" ? m.theme_light() : m.theme_dark()}
      title={mode === "dark" ? m.theme_light() : m.theme_dark()}
      className="rounded-lg border border-border bg-card p-2 text-muted-foreground transition-colors hover:text-foreground"
    >
      {mode === "light" ? (
        <Moon className="h-4 w-4" />
      ) : (
        <Sun className="h-4 w-4" />
      )}
    </button>
  );
}

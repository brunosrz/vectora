import { useEffect, useState } from 'react'
import { Moon, Sun } from 'lucide-react'
import { m } from '#/paraglide/messages'
import {
  applyTheme,
  getStoredTheme,
  resolveTheme,
  setTheme,
  watchSystemTheme,
} from '#/lib/theme'

/** Botão sol/lua que alterna entre os modos claro e escuro (paleta Min). */
export default function ThemeToggle() {
  // Estado efetivo (light/dark) — inicia null no SSR para evitar mismatch.
  const [mode, setMode] = useState<'light' | 'dark' | null>(null)

  useEffect(() => {
    applyTheme(getStoredTheme())
    setMode(resolveTheme(getStoredTheme()))
    return watchSystemTheme()
  }, [])

  const toggle = () => {
    const next = mode === 'dark' ? 'light' : 'dark'
    setTheme(next)
    setMode(next)
  }

  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={mode === 'dark' ? m.theme_light() : m.theme_dark()}
      title={mode === 'dark' ? m.theme_light() : m.theme_dark()}
      className="flex h-[30px] w-[30px] items-center justify-center rounded-2xl bg-card text-foreground/80 shadow-[0px_1px_3px_rgba(24,25,28,0.3),0px_1px_2px_-1px_rgba(24,25,28,0.3)] transition-colors hover:text-foreground"
    >
      {mode === 'light' ? (
        <Moon className="h-4 w-4" />
      ) : (
        <Sun className="h-4 w-4" />
      )}
    </button>
  )
}

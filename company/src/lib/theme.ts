/**
 * theme.ts — modo claro/escuro do site (paleta Min, mesma base do Vectora Chat).
 *
 * Arquitetura: `:root` define o tema escuro; a classe `.light` em <html>
 * sobrescreve os tokens. A classe `.dark` acompanha para a variant Tailwind.
 * A preferência persiste em localStorage; "system" segue prefers-color-scheme.
 */

export type Theme = 'light' | 'dark' | 'system'

export const THEME_STORAGE_KEY = 'vectora-company-theme'

export function getStoredTheme(): Theme {
  if (typeof localStorage === 'undefined') return 'system'
  const value = localStorage.getItem(THEME_STORAGE_KEY)
  return value === 'light' || value === 'dark' ? value : 'system'
}

function systemPrefersDark(): boolean {
  return (
    typeof window !== 'undefined' &&
    window.matchMedia('(prefers-color-scheme: dark)').matches
  )
}

/** Resolve o tema efetivo (light/dark) a partir da preferência salva. */
export function resolveTheme(theme: Theme): 'light' | 'dark' {
  if (theme === 'system') return systemPrefersDark() ? 'dark' : 'light'
  return theme
}

export function applyTheme(theme: Theme): void {
  const dark = resolveTheme(theme) === 'dark'
  const root = document.documentElement
  root.classList.toggle('dark', dark)
  root.classList.toggle('light', !dark)
}

export function setTheme(theme: Theme): void {
  localStorage.setItem(THEME_STORAGE_KEY, theme)
  applyTheme(theme)
}

/**
 * Script inline injetado no <head> para aplicar a classe antes do primeiro
 * paint (anti-FOUC). Mantém a mesma lógica de applyTheme em formato standalone.
 */
export const THEME_INIT_SCRIPT = `(function(){try{var t=localStorage.getItem("${THEME_STORAGE_KEY}");var d=t==="dark"||(t!=="light"&&window.matchMedia("(prefers-color-scheme: dark)").matches);var c=document.documentElement.classList;c.toggle("dark",d);c.toggle("light",!d);}catch(e){}})();`

/** Segue mudanças do SO enquanto a preferência for "system". */
export function watchSystemTheme(): () => void {
  const mq = window.matchMedia('(prefers-color-scheme: dark)')
  const onChange = () => {
    if (getStoredTheme() === 'system') applyTheme('system')
  }
  mq.addEventListener('change', onChange)
  return () => mq.removeEventListener('change', onChange)
}

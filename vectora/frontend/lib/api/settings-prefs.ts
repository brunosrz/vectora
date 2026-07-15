/**
 * Cliente do backend para as preferências durável do usuário (fonte de
 * verdade — CLAUDE.md §8). O settings-store (Zustand) continua com
 * localStorage como cache rápido de primeira pintura; este módulo sincroniza
 * o subconjunto curado de campos com o backend, que sobrevive a reinstalar o
 * app ou limpar o cache do navegador.
 */

export interface FrontendPrefs {
  selectedModel?: string;
  theme?: string;
  language?: string;
  chatMode?: boolean;
  permissionMode?: string;
  reasoningEffort?: string;
  sidebarPosition?: string;
  autoUpdateEnabled?: boolean;
}

/** Busca as preferências salvas no backend; `{}` em qualquer falha de rede. */
export async function fetchPrefs(): Promise<FrontendPrefs> {
  try {
    const res = await fetch("/settings/prefs");
    if (!res.ok) return {};
    return (await res.json()) as FrontendPrefs;
  } catch {
    return {};
  }
}

/**
 * Envia mudanças pro backend (merge parcial). Fire-and-forget por design —
 * chamada não é aguardada pelos setters do settings-store; falha de rede não
 * pode travar a UI, e o valor já está aplicado no cache local.
 */
export async function pushPrefs(changes: FrontendPrefs): Promise<void> {
  try {
    await fetch("/settings/prefs", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(changes),
    });
  } catch {
    /* best-effort — sem retry; a próxima mudança tenta de novo */
  }
}

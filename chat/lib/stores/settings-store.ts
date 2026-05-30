/**
 * settings-store.ts — Bloco L
 *
 * Zustand store para preferências do usuário.
 * Persiste no localStorage com chave prefixada por user_id:
 *   "vectora-settings-{userId}"
 * Permite isolamento de preferências por usuário (auth multi-tenant).
 */

import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

// ---------------------------------------------------------------------------
// Tipos
// ---------------------------------------------------------------------------

export type Verbosity = "concise" | "normal" | "detailed";
export type Theme = "light" | "dark" | "system";
export type Lang = "en" | "es" | "pt";
/** Modos de permissão (R2) — espelham o permission_mode do backend. */
export type PermissionMode =
  | "ask"
  | "accept_edits"
  | "plan"
  | "auto"
  | "bypass";
/** Nível de esforço de raciocínio do modelo (R4). */
export type ReasoningEffort = "low" | "medium" | "high" | "max";

/** Modos de permissão em ordem de exibição no seletor (R2). */
export const PERMISSION_MODES: PermissionMode[] = [
  "ask",
  "accept_edits",
  "plan",
  "auto",
  "bypass",
];

/** Níveis de esforço em ordem de exibição (R4). */
export const REASONING_EFFORTS: ReasoningEffort[] = [
  "low",
  "medium",
  "high",
  "max",
];

/** Idiomas suportados — ordem de exibição no seletor */
export const SUPPORTED_LANGS: { value: Lang; label: string }[] = [
  { value: "en", label: "English" },
  { value: "es", label: "Español" },
  { value: "pt", label: "Português" },
];

/**
 * Detecta idioma preferido do browser; mapeia para o mais próximo suportado.
 * "pt" cobre todo português — pt-BR, pt-PT, pt — já que o Vectora só tem
 * português brasileiro, assim como "en" cobre en-US, en-GB, etc.
 */
function detectLanguage(): Lang {
  if (typeof navigator === "undefined") return "en";
  const lang = navigator.language.toLowerCase();
  if (lang.startsWith("pt")) return "pt";
  if (lang.startsWith("es")) return "es";
  return "en";
}

export interface SettingsState {
  /** Exibir tool calls na interface do chat */
  showToolCalls: boolean;
  /** Solicitar confirmação antes de ações destrutivas (HITL antecipado) */
  requireHitl: boolean;
  /** Nível de detalhe das respostas */
  verbosity: Verbosity;
  /** Tema da interface */
  theme: Theme;
  /** Limite de mensagens exibidas no histórico */
  historyLimit: number;
  /** Instrução personalizada prefixada ao system prompt */
  customSystemPrompt: string;
  /** Idioma da interface */
  language: Lang;
  /** Modo de permissão para ações destrutivas (R2) */
  permissionMode: PermissionMode;
  /** Esforço de raciocínio do modelo (R4) */
  reasoningEffort: ReasoningEffort;
  /** Modo rápido — desliga reasoning/thinking para latência mínima (R4) */
  fastMode: boolean;

  // Ações
  setShowToolCalls: (v: boolean) => void;
  setRequireHitl: (v: boolean) => void;
  setVerbosity: (v: Verbosity) => void;
  setTheme: (v: Theme) => void;
  setHistoryLimit: (v: number) => void;
  setCustomSystemPrompt: (v: string) => void;
  setLanguage: (v: Lang) => void;
  setPermissionMode: (v: PermissionMode) => void;
  setReasoningEffort: (v: ReasoningEffort) => void;
  setFastMode: (v: boolean) => void;
  resetSettings: () => void;
}

// ---------------------------------------------------------------------------
// Defaults
// ---------------------------------------------------------------------------

const DEFAULTS = {
  showToolCalls: false,
  requireHitl: true,
  verbosity: "normal" as Verbosity,
  theme: "system" as Theme,
  historyLimit: 50,
  customSystemPrompt: "",
  language: "en" as Lang, // Sobrescrito pelo detectLanguage() no create()
  permissionMode: "ask" as PermissionMode,
  reasoningEffort: "medium" as ReasoningEffort,
  fastMode: false,
};

// ---------------------------------------------------------------------------
// Chave de storage
// ---------------------------------------------------------------------------

export const SETTINGS_KEY_PREFIX = "vectora-settings-";

/** Retorna a chave do localStorage para o usuário informado.
 *  Sem userId → usa "local" (modo CLI / sem auth). */
export function getStorageKey(userId?: string): string {
  return `${SETTINGS_KEY_PREFIX}${userId ?? "local"}`;
}

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      ...DEFAULTS,
      // Detecta idioma do browser como valor inicial — sobrescrito pelo
      // localStorage ao reidratar se o usuário já havia salvo uma preferência.
      language: detectLanguage(),

      setShowToolCalls: (v) => set({ showToolCalls: v }),
      setRequireHitl: (v) => set({ requireHitl: v }),
      setVerbosity: (v) => set({ verbosity: v }),
      setTheme: (v) => set({ theme: v }),
      setHistoryLimit: (v) => set({ historyLimit: v }),
      setCustomSystemPrompt: (v) => set({ customSystemPrompt: v }),
      setLanguage: (v) => set({ language: v }),
      setPermissionMode: (v) => set({ permissionMode: v }),
      setReasoningEffort: (v) => set({ reasoningEffort: v }),
      setFastMode: (v) => set({ fastMode: v }),
      resetSettings: () => set({ ...DEFAULTS, language: detectLanguage() }),
    }),
    {
      name: getStorageKey(), // Chave default; re-hidratada ao chamar loadUserSettings()
      storage: createJSONStorage(() =>
        typeof window !== "undefined"
          ? localStorage
          : {
              getItem: () => null,
              setItem: () => undefined,
              removeItem: () => undefined,
            },
      ),
      partialize: (state) => ({
        showToolCalls: state.showToolCalls,
        requireHitl: state.requireHitl,
        verbosity: state.verbosity,
        theme: state.theme,
        historyLimit: state.historyLimit,
        customSystemPrompt: state.customSystemPrompt,
        language: state.language,
        permissionMode: state.permissionMode,
        reasoningEffort: state.reasoningEffort,
        fastMode: state.fastMode,
      }),
    },
  ),
);

/**
 * Re-hidrata o store com a chave específica do usuário.
 * Chamar após login para carregar as preferências salvas.
 *
 * @example
 *   loadUserSettings("user_abc123")
 */
export function loadUserSettings(userId?: string): void {
  const key = getStorageKey(userId);
  useSettingsStore.persist.setOptions({ name: key });
  void useSettingsStore.persist.rehydrate();
}

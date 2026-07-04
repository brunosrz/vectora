/**
 * settings-store.ts — preferências do usuário.
 *
 * Persiste no localStorage com chave prefixada por user_id:
 *   "vectora-settings-{userId}"
 * Permite isolamento de preferências por usuário (auth multi-tenant).
 */

import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import type { BaseThemeColors } from "@/lib/theme/presets";

// ---------------------------------------------------------------------------
// Tipos
// ---------------------------------------------------------------------------

export type Verbosity = "concise" | "normal" | "detailed";
export type Theme = "light" | "dark" | "system";
/** "default" = paleta padrão do Vectora; "custom" = `customThemeColors`;
 *  qualquer outro valor é o `id` de um item em `THEME_PRESETS`. */
export type ThemePreset = "default" | "custom" | (string & {});
export type Lang = "en" | "es" | "pt";
/** Lado da sidebar de sessões (workbench fica no lado oposto). */
export type SidebarPosition = "left" | "right";
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
  /** Tema da interface (claro/escuro/sistema) */
  theme: Theme;
  /** Paleta de cores aplicada por cima do tema (presets ou customizada) */
  themePreset: ThemePreset;
  /** Cores base da paleta customizada (quando themePreset === "custom") */
  customThemeColors: BaseThemeColors | null;
  /** Limite de mensagens exibidas no histórico */
  historyLimit: number;
  /** Instrução personalizada prefixada ao system prompt */
  customSystemPrompt: string;
  /** Blocos de instrução de treinamento adicionais (um item por bloco) */
  trainingInstructions: string[];
  /** Idioma da interface */
  language: Lang;
  /** Modo de permissão para ações destrutivas (R2) */
  permissionMode: PermissionMode;
  /** Esforço de raciocínio do modelo (R4) */
  reasoningEffort: ReasoningEffort;
  /** Modo rápido — desliga reasoning/thinking para latência mínima (R4) */
  fastMode: boolean;
  /** Largura da sidebar em px (desktop), arrastável pela borda direita. */
  sidebarWidth: number;
  /** Lado da sidebar de sessões; workbench fica no lado oposto. */
  sidebarPosition: SidebarPosition;
  /** Modo chat puro: oculta workbench, WorkspaceSelector e tools de filesystem. */
  chatMode: boolean;
  /** Sub-modo IDE dentro do Dev: layout VS Code com editor docked. */
  ideMode: boolean;
  /** Largura do painel de chat lateral no modo IDE (px). */
  chatSidebarWidth: number;

  // Ações
  setShowToolCalls: (v: boolean) => void;
  setRequireHitl: (v: boolean) => void;
  setVerbosity: (v: Verbosity) => void;
  setTheme: (v: Theme) => void;
  setThemePreset: (v: ThemePreset) => void;
  setCustomThemeColors: (v: BaseThemeColors | null) => void;
  setHistoryLimit: (v: number) => void;
  setCustomSystemPrompt: (v: string) => void;
  setTrainingInstructions: (v: string[]) => void;
  setLanguage: (v: Lang) => void;
  setPermissionMode: (v: PermissionMode) => void;
  setReasoningEffort: (v: ReasoningEffort) => void;
  setFastMode: (v: boolean) => void;
  setSidebarWidth: (v: number) => void;
  setSidebarPosition: (v: SidebarPosition) => void;
  setChatMode: (v: boolean) => void;
  setIdeMode: (v: boolean) => void;
  setChatSidebarWidth: (v: number) => void;
  resetSettings: () => void;
}

/** Limites de largura da sidebar (px). */
const SIDEBAR_MIN_WIDTH = 180;
const SIDEBAR_MAX_WIDTH = 480;

// ---------------------------------------------------------------------------
// Defaults
// ---------------------------------------------------------------------------

const DEFAULTS = {
  showToolCalls: false,
  requireHitl: true,
  verbosity: "normal" as Verbosity,
  theme: "system" as Theme,
  themePreset: "default" as ThemePreset,
  customThemeColors: null as BaseThemeColors | null,
  historyLimit: 50,
  customSystemPrompt: "",
  trainingInstructions: [] as string[],
  language: "en" as Lang, // Sobrescrito pelo detectLanguage() no create()
  permissionMode: "ask" as PermissionMode,
  reasoningEffort: "medium" as ReasoningEffort,
  fastMode: false,
  sidebarWidth: 224,
  sidebarPosition: "left" as SidebarPosition,
  chatMode: false,
  ideMode: false,
  chatSidebarWidth: 256,
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
      setThemePreset: (v) => set({ themePreset: v }),
      setCustomThemeColors: (v) => set({ customThemeColors: v }),
      setHistoryLimit: (v) => set({ historyLimit: v }),
      setCustomSystemPrompt: (v) => set({ customSystemPrompt: v }),
      setTrainingInstructions: (v) => set({ trainingInstructions: v }),
      setLanguage: (v) => {
        set({ language: v });
        // Sincroniza o locale do Paraglide (recarrega para aplicar o idioma
        // a todas as mensagens m.* renderizadas).
        void import("@/lib/paraglide/runtime").then(
          ({ setLocale, getLocale }) => {
            if (getLocale() !== v) setLocale(v);
          },
        );
      },
      setPermissionMode: (v) => set({ permissionMode: v }),
      setReasoningEffort: (v) => set({ reasoningEffort: v }),
      setFastMode: (v) => set({ fastMode: v }),
      setSidebarWidth: (v) =>
        set({
          sidebarWidth: Math.max(
            SIDEBAR_MIN_WIDTH,
            Math.min(SIDEBAR_MAX_WIDTH, Math.round(v)),
          ),
        }),
      setSidebarPosition: (v) => set({ sidebarPosition: v }),
      setChatMode: (v) => set({ chatMode: v }),
      setIdeMode: (v) => set({ ideMode: v }),
      setChatSidebarWidth: (v) =>
        set({ chatSidebarWidth: Math.max(240, Math.min(800, Math.round(v))) }),
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
        themePreset: state.themePreset,
        customThemeColors: state.customThemeColors,
        historyLimit: state.historyLimit,
        customSystemPrompt: state.customSystemPrompt,
        trainingInstructions: state.trainingInstructions,
        language: state.language,
        permissionMode: state.permissionMode,
        reasoningEffort: state.reasoningEffort,
        fastMode: state.fastMode,
        sidebarWidth: state.sidebarWidth,
        chatMode: state.chatMode,
        ideMode: state.ideMode,
        chatSidebarWidth: state.chatSidebarWidth,
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

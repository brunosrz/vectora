/**
 * settings-dialog-store — controla a abertura do Settings Dialog,
 * a aba ativa e a sub-aba (quando a aba tem painel interno como Admin).
 *
 * Permite deep-link a partir de qualquer lugar (ex.: o menu "+" abrindo
 * direto em Conectores/Plugins, banner de licença em Administração →
 * Configurações) sem prop drilling — o dialog é renderizado uma única vez
 * (no UserMenu) e lê seu estado daqui.
 */

import { create } from "zustand";

export type SettingsTab =
  | "conta"
  | "preferencias"
  | "memoria"
  | "integracoes"
  | "plugins"
  | "skills"
  | "envs"
  | "admin";

/** Sub-abas internas da aba `admin`. */
export type AdminSubTab =
  | "users"
  | "tools"
  | "system"
  | "config"
  | "safe-roots";

interface SettingsDialogState {
  open: boolean;
  tab: SettingsTab;
  /**
   * Sub-aba alvo dentro de `tab`. Hoje só `admin` tem sub-abas; outras
   * abas ignoram o campo. Painéis filhos sincronizam o `active` local
   * com este valor via `useEffect`.
   */
  adminSubTab?: AdminSubTab;
  openAt: (tab?: SettingsTab, adminSubTab?: AdminSubTab) => void;
  setOpen: (v: boolean) => void;
  setTab: (tab: SettingsTab) => void;
  setAdminSubTab: (subTab: AdminSubTab) => void;
}

export const useSettingsDialogStore = create<SettingsDialogState>((set) => ({
  open: false,
  tab: "conta",
  adminSubTab: undefined,
  openAt: (tab = "conta", adminSubTab) => set({ open: true, tab, adminSubTab }),
  setOpen: (v) => set({ open: v }),
  setTab: (tab) => set({ tab }),
  setAdminSubTab: (adminSubTab) => set({ adminSubTab }),
}));

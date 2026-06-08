/**
 * settings-dialog-store — controla a abertura do Settings Dialog
 * (preferências de conta) e a aba ativa.
 *
 * Permite deep-link a partir de qualquer lugar (ex.: o menu "+" abrindo
 * direto em Conectores/Plugins) sem prop drilling — o dialog é renderizado
 * uma única vez (no UserMenu) e lê seu estado daqui.
 *
 * Administração (root/admin only) tem dialog e store próprios — ver
 * `admin-dialog-store` / `AdminDialog` (P4) — por ser um painel de escopo
 * de servidor, não de conta pessoal.
 */

import { create } from "zustand";

export type SettingsTab =
  | "conta"
  | "preferencias"
  | "memoria"
  | "integracoes"
  | "plugins"
  | "skills"
  | "envs";

interface SettingsDialogState {
  open: boolean;
  tab: SettingsTab;
  openAt: (tab?: SettingsTab) => void;
  setOpen: (v: boolean) => void;
  setTab: (tab: SettingsTab) => void;
}

export const useSettingsDialogStore = create<SettingsDialogState>((set) => ({
  open: false,
  tab: "conta",
  openAt: (tab = "conta") => set({ open: true, tab }),
  setOpen: (v) => set({ open: v }),
  setTab: (tab) => set({ tab }),
}));

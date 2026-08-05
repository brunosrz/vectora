/**
 * preferencias-dialog-store — controla a abertura do painel "Preferências"
 * (Preferências, Conta e Memória) e a aba ativa.
 *
 * Permite deep-link a partir de qualquer lugar sem prop drilling — o dialog
 * é renderizado uma única vez (no SettingsMenu) e lê seu estado daqui.
 *
 * "Ambiente" (Envs/Skills/Plugins/Integrações) e "Administração" (root/admin)
 * são painéis próprios — ver `environment-dialog-store` e
 * `administracao-dialog-store`.
 */

import { create } from "zustand";

export type PreferenciasTab =
  "preferencias" | "fallbacks" | "conta" | "memoria";

interface PreferenciasDialogState {
  open: boolean;
  tab: PreferenciasTab;
  openAt: (tab?: PreferenciasTab) => void;
  setOpen: (v: boolean) => void;
  setTab: (tab: PreferenciasTab) => void;
}

export const usePreferenciasDialogStore = create<PreferenciasDialogState>(
  (set) => ({
    open: false,
    tab: "preferencias",
    openAt: (tab = "preferencias") => set({ open: true, tab }),
    setOpen: (v) => set({ open: v }),
    setTab: (tab) => set({ tab }),
  }),
);

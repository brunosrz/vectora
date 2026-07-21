/**
 * environment-dialog-store — controla a abertura do painel "Ambiente"
 * (Integrações, Provider Routing) e a aba ativa.
 *
 * Permite deep-link a partir de qualquer lugar (ex.: o menu "+" abrindo
 * direto em Conectores) sem prop drilling — o dialog é renderizado uma
 * única vez (no SettingsMenu) e lê seu estado daqui.
 *
 * "Preferências" (Conta/Preferências/Memória) e "Administração" (root/admin)
 * são painéis próprios — ver `preferencias-dialog-store` e
 * `administracao-dialog-store`.
 */

import { create } from "zustand";

export type EnvironmentTab = "provider_routing" | "integracoes";

interface EnvironmentDialogState {
  open: boolean;
  tab: EnvironmentTab;
  openAt: (tab?: EnvironmentTab) => void;
  setOpen: (v: boolean) => void;
  setTab: (tab: EnvironmentTab) => void;
}

export const useEnvironmentDialogStore = create<EnvironmentDialogState>(
  (set) => ({
    open: false,
    tab: "integracoes",
    openAt: (tab = "integracoes") => set({ open: true, tab }),
    setOpen: (v) => set({ open: v }),
    setTab: (tab) => set({ tab }),
  }),
);

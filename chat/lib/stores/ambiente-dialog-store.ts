/**
 * ambiente-dialog-store — controla a abertura do painel "Ambiente"
 * (Envs, Skills, Plugins e Integrações) e a aba ativa.
 *
 * Permite deep-link a partir de qualquer lugar (ex.: o menu "+" abrindo
 * direto em Conectores/Plugins) sem prop drilling — o dialog é renderizado
 * uma única vez (no SettingsMenu) e lê seu estado daqui.
 *
 * "Preferências" (Conta/Preferências/Memória) e "Administração" (root/admin)
 * são painéis próprios — ver `preferencias-dialog-store` e
 * `administracao-dialog-store`.
 */

import { create } from "zustand";

export type AmbienteTab = "envs" | "skills" | "plugins" | "integracoes";

interface AmbienteDialogState {
  open: boolean;
  tab: AmbienteTab;
  openAt: (tab?: AmbienteTab) => void;
  setOpen: (v: boolean) => void;
  setTab: (tab: AmbienteTab) => void;
}

export const useAmbienteDialogStore = create<AmbienteDialogState>((set) => ({
  open: false,
  tab: "envs",
  openAt: (tab = "envs") => set({ open: true, tab }),
  setOpen: (v) => set({ open: v }),
  setTab: (tab) => set({ tab }),
}));

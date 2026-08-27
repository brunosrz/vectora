/**
 * administracao-dialog-store — controla a abertura do painel de
 * Administração e a sub-aba ativa (Usuários/Ferramentas/Pastas
 * Seguras/Sistema/Storage).
 *
 * Administração é um dos 3 painéis de configurações (Preferências,
 * Ambiente, Administração), com dialog e store próprios já que o
 * `AdminTab` tem múltiplos sub-painéis e merece navegação independente.
 * Permite deep-link a partir de qualquer lugar (ex.: banner de licença →
 * Administração → Sistema) sem prop drilling.
 */

import { create } from "zustand";
import { useSettingsOverlayStore } from "./settings-overlay-store";

/** Sub-abas internas do painel de Administração. */
export type AdminSubTab =
  "users" | "tools" | "system" | "safe-roots" | "storage";

interface AdminDialogState {
  open: boolean;
  /**
   * Sub-aba alvo na próxima abertura. `AdminTab` sincroniza o `active`
   * local com este valor via `useEffect` e limpa o slot em seguida, para
   * que reaberturas do dialog não fiquem presas na mesma sub-aba.
   */
  subTab?: AdminSubTab;
  openAt: (subTab?: AdminSubTab) => void;
  setOpen: (v: boolean) => void;
  setSubTab: (subTab?: AdminSubTab) => void;
}

export const useAdministracaoDialogStore = create<AdminDialogState>((set) => ({
  open: false,
  subTab: undefined,
  openAt: (subTab) => {
    set({ open: true, subTab });
    useSettingsOverlayStore.getState().openCategory("administracao");
  },
  setOpen: (v) => set({ open: v }),
  setSubTab: (subTab) => set({ subTab }),
}));

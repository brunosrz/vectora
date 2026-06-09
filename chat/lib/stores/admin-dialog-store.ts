/**
 * admin-dialog-store — controla a abertura do painel de Administração e
 * a sub-aba ativa (Usuários/Ferramentas/Pastas Seguras/Sistema/Config).
 *
 * Administração deixou de ser uma aba do `SettingsDialog` (P4) e passou a
 * ser um dialog próprio (`AdminDialog`), já que o `AdminTab` tem múltiplos
 * sub-painéis e merece navegação independente. Permite deep-link a partir
 * de qualquer lugar (ex.: banner de licença → Administração → Config) sem
 * prop drilling, no mesmo padrão de `settings-dialog-store`.
 */

import { create } from "zustand";

/** Sub-abas internas do painel de Administração. */
export type AdminSubTab =
  | "users"
  | "tools"
  | "system"
  | "config"
  | "safe-roots"
  | "storage";

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

export const useAdminDialogStore = create<AdminDialogState>((set) => ({
  open: false,
  subTab: undefined,
  openAt: (subTab) => set({ open: true, subTab }),
  setOpen: (v) => set({ open: v }),
  setSubTab: (subTab) => set({ subTab }),
}));

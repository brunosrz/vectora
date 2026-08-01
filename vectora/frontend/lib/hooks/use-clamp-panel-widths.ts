import { useEffect } from "react";

import { useSettingsStore } from "@/lib/stores/settings-store";
import { useWorkbenchStore } from "@/lib/stores/workbench-store";

//: Reserva mínima pro conteúdo principal (chat/editor) não zerar quando o
//: painel persistido é maior que a viewport atual — mesmo raciocínio do
//: `min-w-0` do Sprint 29, mas pra largura em px persistida, não CSS.
const MIN_MAIN_CONTENT_PX = 320;

/**
 * Um painel resizável persiste a própria largura em px. Se o usuário abriu
 * uma janela larga, redimensionou o painel, e depois volta numa tela
 * estreita (ou encolhe a janela do Electron), a largura antiga persistida
 * pode ultrapassar a viewport inteira — o painel sozinho já causaria
 * overflow horizontal da página. Clampa contra a viewport atual no mount e
 * a cada resize.
 */
export function useClampPanelWidths(): void {
  const chatSidebarWidth = useSettingsStore((s) => s.chatSidebarWidth);
  const setChatSidebarWidth = useSettingsStore((s) => s.setChatSidebarWidth);
  const splitSize = useWorkbenchStore((s) => s.splitSize);
  const setSplitSize = useWorkbenchStore((s) => s.setSplitSize);

  useEffect(() => {
    const clamp = () => {
      const maxWidth = window.innerWidth - MIN_MAIN_CONTENT_PX;
      if (maxWidth <= 0) return;
      if (chatSidebarWidth > maxWidth) setChatSidebarWidth(maxWidth);
      if (splitSize > maxWidth) setSplitSize(maxWidth);
    };

    clamp();
    window.addEventListener("resize", clamp);
    return () => window.removeEventListener("resize", clamp);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chatSidebarWidth, splitSize]);
}

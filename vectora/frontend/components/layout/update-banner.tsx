"use client";

/**
 * Banner de update do Electron — invisível no browser puro.
 *
 * Subscreve a ``window.vectora.onUpdateStatus`` (bridge do preload.ts).
 * Aparece quando há update baixado e oferece "Reiniciar para atualizar".
 *
 * Não aparece em estados intermediários (checking/downloading) — só quando
 * o update está pronto para aplicar. Durante o download, o tray icon
 * mostra progresso (decisão de não roubar atenção do user).
 */

import { useEffect, useState } from "react";
import { Download } from "lucide-react";
import { m } from "@/lib/paraglide/messages";

export function UpdateBanner() {
  const [ready, setReady] = useState(false);
  const [version, setVersion] = useState<string>("");

  useEffect(() => {
    if (typeof window === "undefined" || !window.vectora?.onUpdateStatus) {
      return;
    }
    const unsubscribe = window.vectora.onUpdateStatus((status) => {
      if (status.state === "downloaded") {
        setReady(true);
        if (status.message) setVersion(status.message);
      } else if (status.state === "available" && status.message) {
        setVersion(status.message);
      }
    });
    return unsubscribe;
  }, []);

  if (!ready) return null;

  return (
    <div className="bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border-b border-emerald-500/30 px-4 py-2 text-xs flex items-center gap-2">
      <Download className="w-3.5 h-3.5 shrink-0" />
      <span className="flex-1 min-w-0">
        {version
          ? m.update_banner_ready_with_version({ v: version })
          : m.update_banner_ready()}
      </span>
      <button
        type="button"
        onClick={() => window.vectora?.quitAndInstallUpdate?.()}
        className="px-2 py-0.5 rounded border border-current/40 hover:bg-current/10 transition-colors"
      >
        {m.update_banner_restart()}
      </button>
    </div>
  );
}

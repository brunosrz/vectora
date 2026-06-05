"use client";

/**
 * Banner fixo no topo da app que reflete o status de rede:
 *   - vermelho quando `offline`,
 *   - amarelo "Reconectando…" quando o SSE caiu mas o browser segue online.
 *
 * Ambos os estados são `aria-live="polite"` para anúncio acessível sem
 * interromper o foco do usuário. Quando ambas as flags ficam falsas,
 * o componente não renderiza nada.
 */

import { WifiOff, Loader2 } from "lucide-react";
import { useNetworkStatus } from "@/lib/hooks/use-network-status";

export function NetworkStatusBanner() {
  const { offline, sseReconnecting } = useNetworkStatus();

  if (!offline && !sseReconnecting) return null;

  if (offline) {
    return (
      <div
        role="alert"
        aria-live="polite"
        className="fixed top-0 inset-x-0 z-[55] flex items-center justify-center gap-2 bg-red-600/90 px-4 py-1.5 text-xs font-medium text-white shadow-md backdrop-blur-sm"
      >
        <WifiOff className="h-3.5 w-3.5" aria-hidden />
        <span>
          Sem conexão. Algumas ações estão desabilitadas até o retorno da rede.
        </span>
      </div>
    );
  }

  return (
    <div
      role="status"
      aria-live="polite"
      className="fixed top-0 inset-x-0 z-[55] flex items-center justify-center gap-2 bg-amber-500/90 px-4 py-1.5 text-xs font-medium text-amber-950 shadow-md backdrop-blur-sm"
    >
      <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden />
      <span>Reconectando ao servidor…</span>
    </div>
  );
}

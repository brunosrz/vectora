"use client";

/**
 * AuthProvider — hidrata o auth store no mount.
 *
 * Faz GET /api/auth/me para sincronizar o usuário com o servidor a cada
 * carregamento de página. Usa o sessionStorage como cache para evitar flash.
 */

import { useEffect } from "react";
import { useAuthStore } from "@/lib/stores/auth-store";

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const hydrate = useAuthStore((s) => s.hydrate);

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  return <>{children}</>;
}

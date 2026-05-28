"use client";

/**
 * AuthProvider — hidrata o auth store no mount.
 *
 * Faz GET /api/auth/me para sincronizar o usuário com o servidor a cada
 * carregamento de página. Redireciona para /auth/signin quando o servidor
 * retorna 401 (token expirado, servidor reiniciado, DB recriado etc.).
 */

import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAuthStore } from "@/lib/stores/auth-store";
import { loadUserSettings } from "@/lib/stores/settings-store";

const AUTH_REQUIRED = process.env.NEXT_PUBLIC_VECTORA_AUTH_REQUIRED?.toLowerCase() !== "false";

const PUBLIC_PATHS = ["/auth/signin", "/auth/signup"];

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const hydrate = useAuthStore((s) => s.hydrate);
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!AUTH_REQUIRED) return;
    if (PUBLIC_PATHS.some((p) => pathname.startsWith(p))) return;

    hydrate().then(() => {
      const { isAuthenticated, user } = useAuthStore.getState();
      if (!isAuthenticated) {
        router.replace(`/auth/signin?from=${encodeURIComponent(pathname)}`);
        return;
      }
      // Carrega preferências do usuário autenticado
      loadUserSettings(user?.id);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return <>{children}</>;
}

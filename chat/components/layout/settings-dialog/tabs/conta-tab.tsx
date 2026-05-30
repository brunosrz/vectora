"use client";

/**
 * ContaTab — Bloco L2
 * Exibe email e role do usuário ativo; botão para mudar senha (placeholder).
 */

import { useAuthStore } from "@/lib/stores/auth-store";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";

const ROLE_LABELS: Record<string, string> = {
  root: "Root",
  admin: "Admin",
  member: "Membro",
  viewer: "Visualizador",
};

const ROLE_VARIANTS: Record<
  string,
  "default" | "secondary" | "outline" | "destructive"
> = {
  root: "destructive",
  admin: "default",
  member: "secondary",
  viewer: "outline",
};

export function ContaTab() {
  const user = useAuthStore((s) => s.user);

  if (!user) {
    return (
      <div className="flex flex-col items-center justify-center py-8 text-center">
        <p className="text-sm text-muted-foreground">
          Nenhum usuário autenticado.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Informações da conta */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground font-medium uppercase tracking-wide">
              Email
            </p>
            <p className="text-sm font-mono">{user.email}</p>
          </div>
          <Badge variant={ROLE_VARIANTS[user.role] ?? "secondary"}>
            {ROLE_LABELS[user.role] ?? user.role}
          </Badge>
        </div>
      </div>

      <Separator />

      {/* Ações */}
      <div className="space-y-2">
        <p className="text-xs text-muted-foreground font-medium uppercase tracking-wide">
          Segurança
        </p>
        <Button
          variant="outline"
          size="sm"
          className="w-full justify-start"
          disabled
          title="Em breve"
        >
          Alterar senha
        </Button>
      </div>
    </div>
  );
}

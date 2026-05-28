"use client";

/**
 * EnvsTab — Bloco C10 / L2
 *
 * Tabela de variáveis de ambiente personalizadas do usuário.
 * Cada variável sobrescreve o env do sistema apenas para as requests deste usuário.
 *
 * Implementação completa no Bloco C10; aqui está o esqueleto UI.
 */

import { Settings2 } from "lucide-react";

export function EnvsTab() {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center space-y-3">
      <Settings2 className="w-10 h-10 text-muted-foreground/40" />
      <p className="text-sm font-medium text-muted-foreground">Variáveis de ambiente</p>
      <p className="text-xs text-muted-foreground max-w-[260px]">Configure chaves de API e variáveis de ambiente personalizadas. Elas substituem os valores padrão apenas para suas requisições.</p>
    </div>
  );
}

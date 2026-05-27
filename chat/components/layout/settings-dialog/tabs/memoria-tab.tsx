"use client";

/**
 * MemoriaTab — placeholder para o Bloco N (Per-User Memory).
 *
 * Quando o Bloco N for implementado, este componente exibirá a lista de
 * memórias salvas do usuário com opções de editar e deletar.
 */

import { Brain } from "lucide-react";

export function MemoriaTab() {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center space-y-3">
      <Brain className="w-10 h-10 text-muted-foreground/40" />
      <p className="text-sm font-medium text-muted-foreground">
        Memória personalizada
      </p>
      <p className="text-xs text-muted-foreground max-w-[260px]">
        Em breve você poderá ver e gerenciar o que o Vectora aprendeu sobre você
        nesta seção.
      </p>
    </div>
  );
}

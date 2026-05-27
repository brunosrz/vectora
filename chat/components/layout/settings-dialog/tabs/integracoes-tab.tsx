"use client";

/**
 * IntegracoesTab — placeholder para o Bloco O (Workspace Integrations).
 *
 * Quando o Bloco O for implementado, este componente exibirá cards de
 * integração (GitHub OAuth, OpenAI API key, Anthropic, etc.).
 */

import { Puzzle } from "lucide-react";

export function IntegracoesTab() {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center space-y-3">
      <Puzzle className="w-10 h-10 text-muted-foreground/40" />
      <p className="text-sm font-medium text-muted-foreground">Integrações</p>
      <p className="text-xs text-muted-foreground max-w-[260px]">
        GitHub, OpenAI, Anthropic e outras integrações estarão disponíveis em
        breve nesta seção.
      </p>
    </div>
  );
}

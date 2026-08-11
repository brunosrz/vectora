"use client";

/**
 * WorkbenchSlidePanel — painel interno deslizante, base compartilhada das abas
 * da workbench (Tarefas, Memory/RAG, Context Graph).
 *
 * Renderiza **em fluxo, logo abaixo do botão que o abriu** (não cobre o gatilho),
 * deslizando de cima para baixo e empurrando o conteúdo seguinte — ocupa só o
 * espaço do conteúdo (com scroll a partir de um limite). O próprio botão gatilho
 * continua visível e clicável para colapsar (toggle). Animação de entrada e saída
 * (tailwindcss-animate). Cada consumidor importa esta base e injeta título +
 * conteúdo próprios; a mecânica vive aqui.
 */

import { useEffect, useState, type ReactNode } from "react";
import { X } from "lucide-react";

interface WorkbenchSlidePanelProps {
  open: boolean;
  onClose: () => void;
  /** Título do header (curto). */
  title: ReactNode;
  children: ReactNode;
  /** data-testid do painel (cada consumidor passa o seu). */
  testId?: string;
}

const ANIM_DURATION_MS = 200;

export function WorkbenchSlidePanel({
  open,
  onClose,
  title,
  children,
  testId,
}: WorkbenchSlidePanelProps) {
  // Mantém montado durante a animação de saída antes de desmontar.
  const [rendered, setRendered] = useState(open);
  const [closing, setClosing] = useState(false);

  useEffect(() => {
    if (open) {
      setRendered(true);
      setClosing(false);
      return;
    }
    if (rendered) {
      setClosing(true);
      const t = setTimeout(() => setRendered(false), ANIM_DURATION_MS);
      return () => clearTimeout(t);
    }
  }, [open, rendered]);

  if (!rendered) return null;

  const anim = closing
    ? "animate-out fade-out slide-out-to-top-4"
    : "animate-in fade-in slide-in-from-top-4";

  return (
    <div
      data-testid={testId}
      role="region"
      className={`shrink-0 overflow-hidden border-b border-border bg-popover/60 ${anim}`}
      style={{ animationDuration: `${ANIM_DURATION_MS}ms` }}
    >
      <div className="flex items-center justify-between border-b border-border/60 px-3 py-2">
        <p className="text-xs font-medium text-foreground">{title}</p>
        <button
          onClick={onClose}
          aria-label="Fechar"
          data-testid="slide-panel-close"
          className="flex h-5 w-5 items-center justify-center rounded text-muted-foreground hover:text-foreground hover:bg-muted/50"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      </div>
      {/* resize-y: altura inicial moderada (não os 55vh fixos de antes, que
          dominavam a tela em painéis longos como o de config do RAG) — o
          usuário arrasta a borda inferior pra abrir mais espaço quando
          precisar, min/max evitam colapsar a zero ou estourar a viewport. */}
      <div
        className="resize-y overflow-y-auto p-3"
        style={{ height: "16rem", minHeight: "6rem", maxHeight: "80vh" }}
      >
        {children}
      </div>
    </div>
  );
}

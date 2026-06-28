"use client";

/**
 * WorkbenchSlidePanel — painel interno deslizante, base compartilhada das abas
 * da workbench (Tarefas, Memory/RAG, Context Graph).
 *
 * Em vez de um popover/modal solto, abre como uma "aba oculta" que **desliza de
 * cima para baixo** dentro do próprio painel da aba, ocupando apenas o espaço do
 * conteúdo (com scroll quando passa do limite). Animação de entrada e saída
 * (tailwindcss-animate). Cada consumidor importa esta base e injeta seu título +
 * conteúdo próprios; a mecânica (posição, animação, header, backdrop) vive aqui.
 *
 * Requer um ancestral `relative` (a área de conteúdo da aba) — o painel se
 * posiciona absoluto sobre ela.
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
  /** Direção da animação. "top" desliza de cima (default); "left" da esquerda. */
  from?: "top" | "left";
}

const ANIM_DURATION_MS = 200;

export function WorkbenchSlidePanel({
  open,
  onClose,
  title,
  children,
  testId,
  from = "top",
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

  const enter =
    from === "left" ? "slide-in-from-left-4" : "slide-in-from-top-4";
  const exit = from === "left" ? "slide-out-to-left-4" : "slide-out-to-top-4";
  const panelAnim = closing
    ? `animate-out fade-out ${exit}`
    : `animate-in fade-in ${enter}`;
  const sizing =
    from === "left"
      ? "inset-y-0 left-0 max-w-[90%] w-72 overflow-y-auto"
      : "inset-x-0 top-0 max-h-[85%] overflow-y-auto";

  return (
    <>
      {/* Backdrop sutil — clique fora fecha. */}
      <div
        className={`absolute inset-0 z-20 bg-background/40 ${
          closing ? "animate-out fade-out" : "animate-in fade-in"
        }`}
        style={{ animationDuration: `${ANIM_DURATION_MS}ms` }}
        onClick={onClose}
        aria-hidden
      />
      <div
        data-testid={testId}
        role="dialog"
        className={`absolute z-30 border-border bg-popover shadow-xl ${sizing} ${
          from === "left" ? "border-r" : "border-b"
        } ${panelAnim}`}
        style={{ animationDuration: `${ANIM_DURATION_MS}ms` }}
      >
        <div className="sticky top-0 z-10 flex items-center justify-between border-b border-border/60 bg-popover px-3 py-2">
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
        <div className="p-3">{children}</div>
      </div>
    </>
  );
}

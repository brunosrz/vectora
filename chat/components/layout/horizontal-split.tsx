"use client";

/**
 * HorizontalSplit — split horizontal minimalista para o layout chat/workbench.
 *
 * Substitui `react-resizable-panels` (v4) nesse caso de uso específico.
 * A lib causava `Symbol.iterator undefined` ao reconciliar quando o painel
 * direito alternava entre visível/oculto e quando a hidratação do Zustand
 * persist tornava os defaults instáveis. Para 2 painéis + handle, o custo
 * de manter a lib não compensa.
 *
 * Características:
 * - Painel esquerdo (`left`): ocupa o espaço restante via `flex: 1`.
 * - Painel direito (`right`): largura controlada por `rightSize` em %,
 *   só renderizado quando `showRight=true`. Quando oculto, layout = 100%
 *   esquerda; sem painel residual sobrando 20px e estragando a janela.
 * - `rightCollapsed`: trata o painel direito como a sidebar esquerda
 *   colapsada — mantém uma faixa estreita de largura fixa com borda
 *   divisória, sem handle de resize (nada para arrastar).
 * - Handle: 4px de largura, cursor `col-resize`, arrasta para ajustar
 *   `rightSize` entre `minRight` e `maxRight` (default 20–80).
 * - Imune a SSR: o `right` só é montado após o cliente decidir mostrá-lo;
 *   o tree estável (sempre 1 ou 3 filhos) não precisa de chave de remount.
 */

import { useCallback, useEffect, useRef, type ReactNode } from "react";

interface HorizontalSplitProps {
  left: ReactNode;
  right: ReactNode | null;
  showRight: boolean;
  /** Largura do painel direito em % (0–100). Atualizado durante o drag. */
  rightSize: number;
  onResize: (size: number) => void;
  minRight?: number;
  maxRight?: number;
  className?: string;
  /** Quando true, `right` vira uma faixa estreita de largura fixa (sem resize). */
  rightCollapsed?: boolean;
  /** Largura em px da faixa colapsada. Default: 48 (w-12). */
  collapsedWidth?: number;
}

export function HorizontalSplit({
  left,
  right,
  showRight,
  rightSize,
  onResize,
  minRight = 20,
  maxRight = 80,
  className,
  rightCollapsed = false,
  collapsedWidth = 48,
}: HorizontalSplitProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const draggingRef = useRef(false);

  const onPointerDown = useCallback((e: React.PointerEvent<HTMLDivElement>) => {
    e.preventDefault();
    draggingRef.current = true;
    (e.target as Element).setPointerCapture?.(e.pointerId);
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
  }, []);

  const onPointerMove = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      if (!draggingRef.current) return;
      const rect = containerRef.current?.getBoundingClientRect();
      if (!rect) return;
      const distFromRight = rect.right - e.clientX;
      const pct = (distFromRight / rect.width) * 100;
      const clamped = Math.max(minRight, Math.min(maxRight, pct));
      onResize(clamped);
    },
    [maxRight, minRight, onResize],
  );

  const onPointerUp = useCallback((e: React.PointerEvent<HTMLDivElement>) => {
    if (!draggingRef.current) return;
    draggingRef.current = false;
    (e.target as Element).releasePointerCapture?.(e.pointerId);
    document.body.style.cursor = "";
    document.body.style.userSelect = "";
  }, []);

  // Garante restauração do cursor mesmo se o componente desmontar mid-drag.
  useEffect(() => {
    return () => {
      if (draggingRef.current) {
        document.body.style.cursor = "";
        document.body.style.userSelect = "";
      }
    };
  }, []);

  const rightWidth = Math.max(minRight, Math.min(maxRight, rightSize));

  return (
    <div ref={containerRef} className={`flex h-full ${className ?? ""}`}>
      {/* overflow-visible: dropdowns do appbar (Header) não podem ser
          recortados por este container — o conteúdo rolável (ChatInterface)
          já tem seu próprio overflow-hidden interno. */}
      <div className="flex-1 min-w-0 overflow-visible">{left}</div>
      {showRight && rightCollapsed && (
        <div
          style={{ width: collapsedWidth }}
          className="shrink-0 overflow-hidden border-l border-border/60"
        >
          {right}
        </div>
      )}
      {showRight && !rightCollapsed && (
        <>
          <div
            role="separator"
            aria-orientation="vertical"
            onPointerDown={onPointerDown}
            onPointerMove={onPointerMove}
            onPointerUp={onPointerUp}
            onPointerCancel={onPointerUp}
            className="w-1 bg-border/40 hover:bg-border transition-colors cursor-col-resize shrink-0"
          />
          <div
            style={{ width: `${rightWidth}%` }}
            className="shrink-0 overflow-hidden"
          >
            {right}
          </div>
        </>
      )}
    </div>
  );
}

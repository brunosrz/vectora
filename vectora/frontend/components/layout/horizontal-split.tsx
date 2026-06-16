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
 * - Painel direito (`right`): largura controlada por `rightSize` em px
 *   (mesma unidade da sidebar esquerda), só renderizado quando
 *   `showRight=true`. Quando oculto, layout = 100% esquerda; sem painel
 *   residual sobrando 20px e estragando a janela.
 * - `rightCollapsed`: trata o painel direito como a sidebar esquerda
 *   colapsada — mantém uma faixa estreita de largura fixa com borda
 *   divisória, sem handle de resize (nada para arrastar).
 * - Handle: 4px de largura, cursor `col-resize`, arrasta para ajustar
 *   `rightSize` (px) entre `minRight` e `maxRight`.
 * - Imune a SSR: o `right` só é montado após o cliente decidir mostrá-lo;
 *   o tree estável (sempre 1 ou 3 filhos) não precisa de chave de remount.
 */

import { useCallback, useEffect, useRef, type ReactNode } from "react";

interface HorizontalSplitProps {
  left: ReactNode;
  right: ReactNode | null;
  showRight: boolean;
  /** Largura do painel direito em px. Atualizada durante o drag. */
  rightSize: number;
  onResize: (size: number) => void;
  /** Largura mínima do painel direito em px. */
  minRight?: number;
  /** Largura máxima do painel direito em px. */
  maxRight?: number;
  className?: string;
  /** Quando true, `right` vira uma faixa estreita de largura fixa (sem resize). */
  rightCollapsed?: boolean;
  /** Largura em px da faixa colapsada. Default: 48 (w-12). */
  collapsedWidth?: number;
  /** Lado do painel fixo (`right`). Default "right" (atrás do flex-1). */
  side?: "left" | "right";
}

export function HorizontalSplit({
  left,
  right,
  showRight,
  rightSize,
  onResize,
  minRight = 180,
  maxRight = 720,
  className,
  rightCollapsed = false,
  collapsedWidth = 48,
  side = "right",
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
      const dist =
        side === "left" ? e.clientX - rect.left : rect.right - e.clientX;
      const clamped = Math.max(minRight, Math.min(maxRight, dist));
      onResize(clamped);
    },
    [maxRight, minRight, onResize, side],
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

  const handle = (
    <div
      role="separator"
      aria-orientation="vertical"
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onPointerCancel={onPointerUp}
      className="w-1 bg-border/40 hover:bg-border transition-colors cursor-col-resize shrink-0"
    />
  );
  const fixedPanel = rightCollapsed ? (
    <div
      style={{ width: collapsedWidth }}
      className={`shrink-0 overflow-hidden border-border/60 ${side === "left" ? "border-r" : "border-l"}`}
    >
      {right}
    </div>
  ) : (
    <div style={{ width: rightWidth }} className="shrink-0 overflow-hidden">
      {right}
    </div>
  );

  // overflow-visible: dropdowns do appbar (Header) não podem ser recortados
  // por este container — o conteúdo rolável já tem overflow-hidden interno.
  const flexPanel = (
    <div className="flex-1 min-w-0 overflow-visible">{left}</div>
  );

  return (
    <div ref={containerRef} className={`flex h-full ${className ?? ""}`}>
      {side === "left" && showRight && (
        <>
          {fixedPanel}
          {!rightCollapsed && handle}
        </>
      )}
      {flexPanel}
      {side === "right" && showRight && (
        <>
          {!rightCollapsed && handle}
          {fixedPanel}
        </>
      )}
    </div>
  );
}

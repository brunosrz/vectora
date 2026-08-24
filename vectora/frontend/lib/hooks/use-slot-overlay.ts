import { useLayoutEffect, type RefObject } from "react";

/**
 * Sincroniza posição/tamanho de `overlayRef` (position: absolute, ancorado
 * em `anchorRef`) com o retângulo de `slotEl` — sem `setState`, direto no
 * DOM, pra não re-renderizar a cada resize.
 *
 * Existe pra permitir uma instância de componente única, nunca remontada,
 * "flutuando" por cima de um placeholder que muda de posição/tamanho
 * conforme o layout ativo (ex.: ChatInterface entre os modos Assistente/IDE
 * do Vectora — cada um o hospeda numa coluna de largura/offset diferente).
 * Quando `slotEl` é `null` (nenhum placeholder ativo no momento — ex.: modo
 * Kanban, ou aba mobile do IDE diferente de "chat"), o overlay só some
 * (`visibility: hidden`); o conteúdo continua montado, fora da tela.
 */
export function useSlotOverlay(
  slotEl: HTMLElement | null,
  overlayRef: RefObject<HTMLElement | null>,
  anchorRef: RefObject<HTMLElement | null>,
) {
  useLayoutEffect(() => {
    const overlay = overlayRef.current;
    const anchor = anchorRef.current;
    if (!overlay || !anchor) return;

    if (!slotEl) {
      overlay.style.visibility = "hidden";
      return;
    }

    const sync = () => {
      const anchorRect = anchor.getBoundingClientRect();
      const slotRect = slotEl.getBoundingClientRect();
      overlay.style.top = `${slotRect.top - anchorRect.top}px`;
      overlay.style.left = `${slotRect.left - anchorRect.left}px`;
      overlay.style.width = `${slotRect.width}px`;
      overlay.style.height = `${slotRect.height}px`;
      overlay.style.visibility = "visible";
    };

    sync();
    const observer = new ResizeObserver(sync);
    observer.observe(slotEl);
    observer.observe(anchor);
    return () => observer.disconnect();
  }, [slotEl, overlayRef, anchorRef]);
}

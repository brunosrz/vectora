"use client";

/**
 * ResizableDialogContent — wrapper para diálogos redimensionáveis.
 *
 * Mantém todos os primitivos Radix (DialogPortal, Overlay, Content) intactos
 * para preservar acessibilidade (focus-trap, aria-modal, fechar com Esc).
 * O redimensionamento é feito por um handle no canto inferior-direito usando
 * pointer-capture — mesmo padrão de horizontal-split e vertical-split.
 *
 * Props extras:
 *   defaultWidth  — largura inicial em px (padrão: 600)
 *   defaultHeight — altura inicial em px (padrão: 560)
 *   minWidth      — mínimo em px (padrão: 380)
 *   minHeight     — mínimo em px (padrão: 300)
 */

import * as React from "react";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import { GripHorizontal, XIcon } from "lucide-react";

import { cn } from "@/lib/utils";

interface ResizableDialogContentProps extends React.ComponentProps<
  typeof DialogPrimitive.Content
> {
  defaultWidth?: number;
  defaultHeight?: number;
  minWidth?: number;
  minHeight?: number;
  showCloseButton?: boolean;
}

export function ResizableDialogContent({
  className,
  children,
  defaultWidth = 600,
  defaultHeight = 560,
  minWidth = 380,
  minHeight = 300,
  showCloseButton = true,
  style,
  ...props
}: ResizableDialogContentProps) {
  const [size, setSize] = React.useState({
    w: defaultWidth,
    h: defaultHeight,
  });
  const dragging = React.useRef(false);
  const startRef = React.useRef({ x: 0, y: 0, w: 0, h: 0 });

  const onPointerDown = (e: React.PointerEvent<HTMLDivElement>) => {
    e.preventDefault();
    dragging.current = true;
    startRef.current = { x: e.clientX, y: e.clientY, w: size.w, h: size.h };
    (e.currentTarget as Element).setPointerCapture(e.pointerId);
  };

  const onPointerMove = (e: React.PointerEvent<HTMLDivElement>) => {
    if (!dragging.current) return;
    const dx = e.clientX - startRef.current.x;
    const dy = e.clientY - startRef.current.y;
    setSize({
      w: Math.max(minWidth, startRef.current.w + dx),
      h: Math.max(minHeight, startRef.current.h + dy),
    });
  };

  const onPointerUp = (e: React.PointerEvent<HTMLDivElement>) => {
    dragging.current = false;
    (e.currentTarget as Element).releasePointerCapture(e.pointerId);
  };

  return (
    <DialogPrimitive.Portal>
      <DialogPrimitive.Overlay className="data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 fixed inset-0 z-50 bg-black/50" />
      <DialogPrimitive.Content
        data-slot="dialog-content"
        className={cn(
          "bg-background data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95",
          "fixed top-[50%] left-[50%] z-50 -translate-x-1/2 -translate-y-1/2",
          "flex flex-col rounded-lg border shadow-lg duration-200 overflow-hidden",
          className,
        )}
        style={{ width: size.w, height: size.h, ...style }}
        {...props}
      >
        {children}

        {showCloseButton && (
          <DialogPrimitive.Close className="ring-offset-background focus:ring-ring data-[state=open]:bg-accent data-[state=open]:text-muted-foreground absolute top-4 right-4 rounded-xs opacity-70 transition-opacity hover:opacity-100 focus:ring-2 focus:ring-offset-2 focus:outline-hidden disabled:pointer-events-none [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4">
            <XIcon />
            <span className="sr-only">Fechar</span>
          </DialogPrimitive.Close>
        )}

        {/* Handle de redimensionamento — canto inferior direito */}
        <div
          role="separator"
          aria-label="Redimensionar diálogo"
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={onPointerUp}
          onPointerCancel={onPointerUp}
          className="absolute bottom-0 right-0 w-5 h-5 cursor-se-resize flex items-center justify-center text-muted-foreground/40 hover:text-muted-foreground/70 transition-colors select-none"
        >
          <GripHorizontal className="w-3 h-3 rotate-45" />
        </div>
      </DialogPrimitive.Content>
    </DialogPrimitive.Portal>
  );
}

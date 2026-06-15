"use client";

/**
 * FileWindow — uma janela flutuante (app da workstation) com um arquivo aberto.
 * Arrastável pela barra de título e redimensionável (8 handles) via react-rnd;
 * a posição/tamanho voltam ao windows-store. O corpo é o FileViewer (mídia ou
 * texto read-only).
 */

import { Rnd } from "react-rnd";
import { Minus, X } from "lucide-react";

import { FileViewer } from "@/components/workbench/file-viewer";
import {
  useWindowsStore,
  type FileWindowState,
} from "@/lib/stores/windows-store";
import { useT } from "@/lib/i18n";

const TITLE_BAR_CLASS = "vectora-window-drag-handle";

export function FileWindow({ win }: { win: FileWindowState }) {
  const t = useT();
  const focus = useWindowsStore((s) => s.focus);
  const close = useWindowsStore((s) => s.close);
  const minimize = useWindowsStore((s) => s.minimize);
  const setBounds = useWindowsStore((s) => s.setBounds);

  return (
    <Rnd
      size={{ width: win.w, height: win.h }}
      position={{ x: win.x, y: win.y }}
      minWidth={280}
      minHeight={180}
      bounds="window"
      dragHandleClassName={TITLE_BAR_CLASS}
      style={{ zIndex: win.zIndex }}
      onMouseDown={() => focus(win.id)}
      onDragStop={(_e, d) => setBounds(win.id, { x: d.x, y: d.y })}
      onResizeStop={(_e, _dir, ref, _delta, pos) =>
        setBounds(win.id, {
          w: ref.offsetWidth,
          h: ref.offsetHeight,
          x: pos.x,
          y: pos.y,
        })
      }
      className="pointer-events-auto"
    >
      <div className="flex flex-col h-full rounded-lg border border-border bg-card shadow-2xl overflow-hidden">
        <div
          className={`${TITLE_BAR_CLASS} flex items-center gap-2 px-2 h-8 shrink-0 bg-muted/40 border-b border-border/60 cursor-move select-none`}
        >
          <span
            className="flex-1 truncate text-xs font-medium"
            title={win.path}
          >
            {win.title}
          </span>
          <button
            onClick={() => minimize(win.id)}
            className="p-1 rounded text-muted-foreground hover:text-foreground hover:bg-muted/60"
            aria-label={t("window.minimize")}
            title={t("window.minimize")}
          >
            <Minus className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => close(win.id)}
            className="p-1 rounded text-muted-foreground hover:text-destructive hover:bg-muted/60"
            aria-label={t("window.close")}
            title={t("window.close")}
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
        <div className="flex-1 min-h-0 bg-background">
          <FileViewer workspaceId={win.workspaceId} path={win.path} />
        </div>
      </div>
    </Rnd>
  );
}

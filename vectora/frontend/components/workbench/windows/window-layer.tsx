"use client";

/**
 * WindowLayer — overlay fixo que renderiza as janelas flutuantes (não
 * minimizadas) sobre todo o app. `pointer-events-none` no overlay deixa o
 * clique passar para o app onde não há janela; cada janela reativa os eventos.
 */

import { useWindowsStore } from "@/lib/stores/windows-store";
import { useSettingsStore } from "@/lib/stores/settings-store";
import { FileWindow } from "./file-window";

export function WindowLayer() {
  const ideMode = useSettingsStore((s) => s.ideMode);
  const windows = useWindowsStore((s) => s.windows);
  const visible = windows.filter((w) => !w.minimized);
  if (ideMode || visible.length === 0) return null;
  return (
    <div className="pointer-events-none fixed inset-0 z-[60]">
      {visible.map((win) => (
        <FileWindow key={win.id} win={win} />
      ))}
    </div>
  );
}

/**
 * windows-store — janelas flutuantes da "workstation".
 *
 * Cada arquivo aberto como app vira uma janela (`<Rnd>`) que flutua sobre todo
 * o Vectora, com posição/tamanho/minimização/z-order persistidos por usuário
 * (chave `vectora-windows-{user_id}`). O conteúdo (FileViewer) é remontado a
 * partir de `{workspaceId, path}` — nada de DOM persistido.
 */

import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";

export interface FileWindowState {
  id: string;
  workspaceId: string;
  path: string;
  /** Nome curto exibido na barra de título e no dock. */
  title: string;
  x: number;
  y: number;
  w: number;
  h: number;
  minimized: boolean;
  zIndex: number;
}

interface WindowsState {
  windows: FileWindowState[];
  /** Maior zIndex já atribuído (cresce ao focar). */
  topZ: number;

  open: (workspaceId: string, path: string) => void;
  close: (id: string) => void;
  focus: (id: string) => void;
  minimize: (id: string) => void;
  restore: (id: string) => void;
  setBounds: (
    id: string,
    bounds: Partial<Pick<FileWindowState, "x" | "y" | "w" | "h">>,
  ) => void;
}

const BASE_Z = 100;

function windowId(workspaceId: string, path: string): string {
  return `${workspaceId}::${path}`;
}

export const useWindowsStore = create<WindowsState>()(
  persist(
    (set, get) => ({
      windows: [],
      topZ: BASE_Z,

      open: (workspaceId, path) =>
        set((s) => {
          const id = windowId(workspaceId, path);
          const z = s.topZ + 1;
          const existing = s.windows.find((w) => w.id === id);
          if (existing) {
            // Já aberta: restaura, foca e traz pro topo.
            return {
              topZ: z,
              windows: s.windows.map((w) =>
                w.id === id ? { ...w, minimized: false, zIndex: z } : w,
              ),
            };
          }
          const count = s.windows.length;
          const next: FileWindowState = {
            id,
            workspaceId,
            path,
            title: path.split("/").pop() || path,
            // Cascata leve para janelas novas não empilharem exatamente.
            x: 80 + (count % 6) * 32,
            y: 80 + (count % 6) * 32,
            w: 640,
            h: 460,
            minimized: false,
            zIndex: z,
          };
          return { topZ: z, windows: [...s.windows, next] };
        }),

      close: (id) =>
        set((s) => ({ windows: s.windows.filter((w) => w.id !== id) })),

      focus: (id) =>
        set((s) => {
          const w = s.windows.find((x) => x.id === id);
          if (!w || w.zIndex === s.topZ) return s;
          const z = s.topZ + 1;
          return {
            topZ: z,
            windows: s.windows.map((x) =>
              x.id === id ? { ...x, zIndex: z } : x,
            ),
          };
        }),

      minimize: (id) =>
        set((s) => ({
          windows: s.windows.map((w) =>
            w.id === id ? { ...w, minimized: true } : w,
          ),
        })),

      restore: (id) =>
        set((s) => {
          const z = s.topZ + 1;
          return {
            topZ: z,
            windows: s.windows.map((w) =>
              w.id === id ? { ...w, minimized: false, zIndex: z } : w,
            ),
          };
        }),

      setBounds: (id, bounds) =>
        set((s) => ({
          windows: s.windows.map((w) =>
            w.id === id ? { ...w, ...bounds } : w,
          ),
        })),
    }),
    {
      name: "vectora-windows",
      storage: createJSONStorage(() =>
        typeof window !== "undefined"
          ? localStorage
          : {
              getItem: () => null,
              setItem: () => {},
              removeItem: () => {},
            },
      ),
    },
  ),
);

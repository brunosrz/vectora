/**
 * windows-store — janelas flutuantes da "workstation".
 *
 * Uma janela por workspace (id = workspaceId). Cada janela suporta múltiplas
 * abas (tabs). Abrir um arquivo já aberto na mesma janela apenas ativa a aba;
 * abrir um arquivo novo adiciona uma aba. Fechar a última aba fecha a janela.
 * Posição/tamanho/minimização persists por usuário em localStorage.
 */

import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";

export interface FileWindowState {
  /** workspaceId — uma janela por workspace */
  id: string;
  workspaceId: string;
  /** Caminhos de arquivo abertos como abas (na ordem de abertura). */
  tabs: string[];
  /** Aba atualmente visível. */
  activeTab: string;
  /** Basename da aba ativa, exibido na barra de título e no dock. */
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

  /** Estado do editor docked (modo IDE). */
  dockedWorkspaceId: string | null;
  dockedTabs: string[];
  dockedActiveTab: string | null;

  /** Abre path na janela do workspace. Cria a janela se não existir, ou
   * adiciona uma aba se a janela já existir. */
  open: (workspaceId: string, path: string) => void;
  /** Fecha a janela inteira (todas as abas). */
  close: (id: string) => void;
  /** Fecha todas as janelas (reset ao iniciar nova conversa / apagar sessão). */
  closeAll: () => void;
  /** Remove uma aba. Se for a última, fecha a janela. */
  closeTab: (id: string, path: string) => void;
  /** Ativa uma aba existente na janela. */
  setActiveTab: (id: string, path: string) => void;
  focus: (id: string) => void;
  minimize: (id: string) => void;
  restore: (id: string) => void;
  setBounds: (
    id: string,
    bounds: Partial<Pick<FileWindowState, "x" | "y" | "w" | "h">>,
  ) => void;

  /** Abre path no editor docked (modo IDE). Reseta tabs ao trocar workspace. */
  openDocked: (workspaceId: string, path: string) => void;
  setDockedActiveTab: (path: string) => void;
  /** Fecha uma tab docked; última tab → zera tudo. */
  closeDockedTab: (path: string) => void;
}

const BASE_Z = 100;

function basename(path: string): string {
  return path.split(/[/\\]/).pop() || path;
}

export const useWindowsStore = create<WindowsState>()(
  persist(
    (set, get) => ({
      windows: [],
      topZ: BASE_Z,
      dockedWorkspaceId: null,
      dockedTabs: [],
      dockedActiveTab: null,

      openDocked: (workspaceId, path) =>
        set((s) => {
          if (s.dockedWorkspaceId !== workspaceId) {
            return {
              dockedWorkspaceId: workspaceId,
              dockedTabs: [path],
              dockedActiveTab: path,
            };
          }
          const tabs = s.dockedTabs.includes(path)
            ? s.dockedTabs
            : [...s.dockedTabs, path];
          return { dockedTabs: tabs, dockedActiveTab: path };
        }),

      setDockedActiveTab: (path) =>
        set((s) =>
          s.dockedTabs.includes(path) ? { dockedActiveTab: path } : s,
        ),

      closeDockedTab: (path) =>
        set((s) => {
          const tabs = s.dockedTabs.filter((t) => t !== path);
          if (tabs.length === 0) {
            return {
              dockedWorkspaceId: null,
              dockedTabs: [],
              dockedActiveTab: null,
            };
          }
          const activeTab =
            s.dockedActiveTab === path
              ? tabs[Math.max(0, s.dockedTabs.indexOf(path) - 1)] ?? tabs[0]
              : s.dockedActiveTab;
          return { dockedTabs: tabs, dockedActiveTab: activeTab };
        }),

      open: (workspaceId, path) =>
        set((s) => {
          const id = workspaceId;
          const z = s.topZ + 1;
          const existing = s.windows.find((w) => w.id === id);

          if (existing) {
            const tabs = existing.tabs.includes(path)
              ? existing.tabs
              : [...existing.tabs, path];
            return {
              topZ: z,
              windows: s.windows.map((w) =>
                w.id === id
                  ? {
                      ...w,
                      tabs,
                      activeTab: path,
                      title: basename(path),
                      minimized: false,
                      zIndex: z,
                    }
                  : w,
              ),
            };
          }

          const count = s.windows.length;
          const next: FileWindowState = {
            id,
            workspaceId,
            tabs: [path],
            activeTab: path,
            title: basename(path),
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

      closeAll: () => set({ windows: [] }),

      closeTab: (id, path) =>
        set((s) => {
          const win = s.windows.find((w) => w.id === id);
          if (!win) return s;
          const tabs = win.tabs.filter((t) => t !== path);
          if (tabs.length === 0) {
            return { windows: s.windows.filter((w) => w.id !== id) };
          }
          const activeTab =
            win.activeTab === path
              ? tabs[Math.max(0, win.tabs.indexOf(path) - 1)] ?? tabs[0]
              : win.activeTab;
          return {
            windows: s.windows.map((w) =>
              w.id === id
                ? { ...w, tabs, activeTab, title: basename(activeTab) }
                : w,
            ),
          };
        }),

      setActiveTab: (id, path) =>
        set((s) => ({
          windows: s.windows.map((w) =>
            w.id === id && w.tabs.includes(path)
              ? { ...w, activeTab: path, title: basename(path) }
              : w,
          ),
        })),

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

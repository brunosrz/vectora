/**
 * workbench-store — Bloco T cont. (T5)
 *
 * Estado do painel lateral multi-aba (Terminal · Arquivos · Diff · Plano),
 * mantendo retro-compatibilidade com o terminals-store original (T3):
 * todos os campos/ações de terminal continuam aqui — agora acompanhados da
 * aba ativa por sessão.
 *
 * O xterm.js e o WebSocket continuam vivendo em refs dentro do componente —
 * o store guarda apenas metadados compartilhados.
 */

import { create } from "zustand";

/** Referência estável de lista vazia (evita criar novo [] a cada selector). */
const EMPTY_LIST: TerminalInstance[] = [];

export interface TerminalInstance {
  /** ID do terminal no backend (pty_registry). */
  id: string;
  /** Título exibido na aba interna do terminal. */
  title: string;
  /** Workspace ao qual o terminal está atrelado. */
  workspaceId: string;
}

/** Abas do workbench (espelha a referência Claude Code). */
export type WorkbenchTab = "terminal" | "files" | "diff" | "plan";

export const WORKBENCH_TABS: WorkbenchTab[] = [
  "terminal",
  "files",
  "diff",
  "plan",
];

interface WorkbenchState {
  // ── Terminal (T1–T4) ─────────────────────────────────────────────────────
  /** terminais por sessão (threadId -> instâncias) */
  byThread: Record<string, TerminalInstance[]>;
  /** terminal ativo (foco) por sessão */
  activeByThread: Record<string, string | null>;
  /** painel aberto na sessão atual (persistido por sessão também) */
  panelOpen: Record<string, boolean>;

  list: (threadId: string) => TerminalInstance[];
  active: (threadId: string) => TerminalInstance | null;
  isOpen: (threadId: string) => boolean;

  open: (threadId: string, instance: TerminalInstance) => void;
  close: (threadId: string, id: string) => void;
  setActive: (threadId: string, id: string) => void;
  togglePanel: (threadId: string) => void;
  setPanelOpen: (threadId: string, open: boolean) => void;

  // ── Workbench (T5) ───────────────────────────────────────────────────────
  /** Aba ativa do workbench por sessão. */
  activeTabByThread: Record<string, WorkbenchTab>;
  getActiveTab: (threadId: string) => WorkbenchTab;
  setActiveTab: (threadId: string, tab: WorkbenchTab) => void;
}

export const useWorkbenchStore = create<WorkbenchState>((set, get) => ({
  byThread: {},
  activeByThread: {},
  panelOpen: {},
  activeTabByThread: {},

  list: (threadId) => get().byThread[threadId] ?? EMPTY_LIST,
  active: (threadId) => {
    const list = get().byThread[threadId] ?? EMPTY_LIST;
    const id = get().activeByThread[threadId];
    return list.find((t) => t.id === id) ?? list[0] ?? null;
  },
  isOpen: (threadId) => Boolean(get().panelOpen[threadId]),

  open: (threadId, instance) =>
    set((s) => {
      const existing = s.byThread[threadId] ?? [];
      if (existing.some((t) => t.id === instance.id)) {
        return {
          activeByThread: { ...s.activeByThread, [threadId]: instance.id },
          panelOpen: { ...s.panelOpen, [threadId]: true },
          activeTabByThread: {
            ...s.activeTabByThread,
            [threadId]: "terminal",
          },
        };
      }
      return {
        byThread: {
          ...s.byThread,
          [threadId]: [...existing, instance],
        },
        activeByThread: { ...s.activeByThread, [threadId]: instance.id },
        panelOpen: { ...s.panelOpen, [threadId]: true },
        activeTabByThread: { ...s.activeTabByThread, [threadId]: "terminal" },
      };
    }),

  close: (threadId, id) =>
    set((s) => {
      const filtered = (s.byThread[threadId] ?? []).filter((t) => t.id !== id);
      const wasActive = s.activeByThread[threadId] === id;
      return {
        byThread: { ...s.byThread, [threadId]: filtered },
        activeByThread: {
          ...s.activeByThread,
          [threadId]: wasActive
            ? (filtered[0]?.id ?? null)
            : s.activeByThread[threadId],
        },
      };
    }),

  setActive: (threadId, id) =>
    set((s) => ({ activeByThread: { ...s.activeByThread, [threadId]: id } })),

  togglePanel: (threadId) =>
    set((s) => ({
      panelOpen: { ...s.panelOpen, [threadId]: !s.panelOpen[threadId] },
    })),

  setPanelOpen: (threadId, open) =>
    set((s) => ({ panelOpen: { ...s.panelOpen, [threadId]: open } })),

  getActiveTab: (threadId) => get().activeTabByThread[threadId] ?? "terminal",
  setActiveTab: (threadId, tab) =>
    set((s) => ({
      activeTabByThread: { ...s.activeTabByThread, [threadId]: tab },
      panelOpen: { ...s.panelOpen, [threadId]: true },
    })),
}));

// ── Retro-compat (T3) ─────────────────────────────────────────────────────
// Mantém o nome legado para componentes que ainda não migraram.
export const useTerminalsStore = useWorkbenchStore;

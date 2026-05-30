/**
 * terminals-store — Bloco T (T3)
 *
 * Metadados dos terminais embarcados por sessão (threadId). O xterm.js e o
 * WebSocket vivem em refs dentro do componente — o store guarda só o que
 * precisa ser compartilhado (lista de instâncias, terminal ativo, painel
 * aberto/fechado, persistente).
 */

import { create } from "zustand";

/** Referência estável de lista vazia (evita criar novo [] a cada selector). */
const EMPTY_LIST: TerminalInstance[] = [];

export interface TerminalInstance {
  /** ID do terminal no backend (pty_registry). */
  id: string;
  /** Título exibido na aba. */
  title: string;
  /** Workspace ao qual o terminal está atrelado. */
  workspaceId: string;
}

interface TerminalsState {
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
}

export const useTerminalsStore = create<TerminalsState>((set, get) => ({
  byThread: {},
  activeByThread: {},
  panelOpen: {},

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
        };
      }
      return {
        byThread: {
          ...s.byThread,
          [threadId]: [...existing, instance],
        },
        activeByThread: { ...s.activeByThread, [threadId]: instance.id },
        panelOpen: { ...s.panelOpen, [threadId]: true },
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
}));

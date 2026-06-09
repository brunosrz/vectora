/**
 * workbench-store — estado do painel lateral multi-aba
 * (Terminal · Arquivos · Diff · Plano).
 *
 * Estrutura em duas camadas:
 *   1. **Shell persistido** (zustand/middleware/persist) — sobrevive reload:
 *      painel aberto/fechado, aba ativa, terminais (metadados), tamanho do
 *      split, pins. Chave `vectora-workbench-{user_id}`.
 *   2. **Caches voláteis** das abas Files/Diff/Plan — sobrevivem a remount
 *      e troca de aba (igual ao threads-store), mas não a reload. SWR pattern:
 *      render imediato do cache, refetch silencioso se stale.
 *
 * O xterm.js e o WebSocket continuam vivendo em refs dentro do componente;
 * o store guarda apenas metadados compartilhados.
 */

import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";
import { immer } from "zustand/middleware/immer";

/** Referência estável de lista vazia (evita criar novo [] a cada selector). */
const EMPTY_LIST: TerminalInstance[] = [];
/** Janela default para considerar uma entrada do cache "stale" (ms). */
export const WORKBENCH_STALE_MS = 30_000;

// ---------------------------------------------------------------------------
// Tipos compartilhados
// ---------------------------------------------------------------------------

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

// ── Files cache ────────────────────────────────────────────────────────────

export interface FileEntry {
  name: string;
  path: string;
  kind: "dir" | "file";
  size?: number;
}

export interface FileContent {
  path: string;
  kind: "text" | "binary";
  content?: string;
  size: number;
  truncated?: boolean;
  /** sha256 do conteúdo — ausente quando truncado (edição fica desabilitada). */
  sha256?: string | null;
}

interface FilesCache {
  /** Diretórios atualmente expandidos (path relativo). */
  expandedDirs: string[];
  /** Entradas de cada diretório já carregado. */
  entriesByDir: Record<string, FileEntry[]>;
  /** Arquivo atualmente aberto no viewer (ou null). */
  openPath: string | null;
  /** Conteúdo de até 8 arquivos abertos recentemente (LRU implícito). */
  contents: Record<string, FileContent>;
  /** Filtro de busca (vive enquanto a aba viver). */
  filter: string;
  /** Timestamp da última carga de cada diretório. */
  fetchedAt: Record<string, number>;
}

// ── Diff cache ─────────────────────────────────────────────────────────────

export interface DiffFile {
  path: string;
  status: "M" | "A" | "D" | "R" | "?";
  additions: number;
  deletions: number;
  /** Flag staged (índice) — char do git status, ou null. Schema 2. */
  staged_change?: string | null;
  /** Flag unstaged (working tree) — char do git status, ou null. Schema 2. */
  unstaged_change?: string | null;
  /** Arquivo não rastreado. Schema 2. */
  untracked?: boolean;
}

export interface DiffHunk {
  header: string;
  lines: string[];
}

export interface DiffSummary {
  is_git_repo: boolean;
  total_additions: number;
  total_deletions: number;
  files: DiffFile[];
}

interface DiffCache {
  summary: DiffSummary | null;
  openFiles: string[];
  hunksByFile: Record<string, DiffHunk[]>;
  summaryFetchedAt: number;
  fileFetchedAt: Record<string, number>;
}

// ── Plan cache ─────────────────────────────────────────────────────────────

export interface PlanItem {
  title: string;
  path: string;
  session_id: string;
  created_at: string;
  content_preview?: string | null;
}

interface PlanCache {
  items: PlanItem[];
  openSlug: string | null;
  contentsBySlug: Record<string, string>;
  fetchedAt: number;
}

// ---------------------------------------------------------------------------
// Estado do store
// ---------------------------------------------------------------------------

interface WorkbenchState {
  // ── Shell persistido ──────────────────────────────────────────────────────
  byThread: Record<string, TerminalInstance[]>;
  activeByThread: Record<string, string | null>;
  panelOpen: Record<string, boolean>;
  activeTabByThread: Record<string, WorkbenchTab>;
  /** Tamanho do painel direito como % (default 40). */
  splitSize: number;
  /** Arquivos fixados por sessão. */
  pinnedFiles: Record<string, string[]>;

  list: (threadId: string) => TerminalInstance[];
  active: (threadId: string) => TerminalInstance | null;
  isOpen: (threadId: string) => boolean;

  open: (threadId: string, instance: TerminalInstance) => void;
  close: (threadId: string, id: string) => void;
  setActive: (threadId: string, id: string) => void;
  togglePanel: (threadId: string) => void;
  setPanelOpen: (threadId: string, open: boolean) => void;

  getActiveTab: (threadId: string) => WorkbenchTab;
  setActiveTab: (threadId: string, tab: WorkbenchTab) => void;

  setSplitSize: (size: number) => void;

  togglePinned: (threadId: string, path: string) => void;
  isPinned: (threadId: string, path: string) => boolean;

  // ── Caches voláteis ───────────────────────────────────────────────────────
  files: Record<string, FilesCache>;
  diff: Record<string, DiffCache>;
  plan: Record<string, PlanCache>;

  // Files
  getFiles: (wsId: string) => FilesCache;
  setFilesEntries: (wsId: string, path: string, entries: FileEntry[]) => void;
  toggleExpanded: (wsId: string, path: string) => void;
  setOpenFile: (wsId: string, path: string | null) => void;
  setFileContent: (wsId: string, path: string, content: FileContent) => void;
  setFilesFilter: (wsId: string, filter: string) => void;
  invalidateFiles: (wsId?: string) => void;

  // Diff
  getDiff: (wsId: string) => DiffCache;
  setDiffSummary: (wsId: string, summary: DiffSummary) => void;
  setDiffOpenFile: (wsId: string, path: string, open: boolean) => void;
  setDiffHunks: (wsId: string, path: string, hunks: DiffHunk[]) => void;
  invalidateDiff: (wsId?: string) => void;

  // Plan
  getPlan: (threadId: string) => PlanCache;
  setPlanItems: (threadId: string, items: PlanItem[]) => void;
  setPlanOpenSlug: (threadId: string, slug: string | null) => void;
  setPlanContent: (threadId: string, slug: string, content: string) => void;
  invalidatePlan: (threadId?: string) => void;

  // Pendência de atualização por aba (volátil). Marcada quando uma tool do
  // agente edita o workspace e a aba Files/Diff não está montada; limpa
  // quando a aba é aberta e revalida.
  pending: Record<string, { files: boolean; diff: boolean }>;
  markPending: (wsId: string) => void;
  clearPending: (wsId: string, key: "files" | "diff") => void;
}

// Caches default usados pelos getters quando uma chave ainda não existe.
// Referências estáveis para não disparar re-renders em consumidores que
// fazem `s.getFiles(wsId)` sem haver entradas.
const EMPTY_FILES: FilesCache = {
  expandedDirs: [],
  entriesByDir: {},
  openPath: null,
  contents: {},
  filter: "",
  fetchedAt: {},
};
const EMPTY_DIFF: DiffCache = {
  summary: null,
  openFiles: [],
  hunksByFile: {},
  summaryFetchedAt: 0,
  fileFetchedAt: {},
};
const EMPTY_PLAN: PlanCache = {
  items: [],
  openSlug: null,
  contentsBySlug: {},
  fetchedAt: 0,
};

// LRU simples: mantém só os últimos 8 conteúdos por workspace.
function pruneContents(
  contents: Record<string, FileContent>,
  keepLast = 8,
): Record<string, FileContent> {
  const keys = Object.keys(contents);
  if (keys.length <= keepLast) return contents;
  // Ordem de inserção (preservada por objetos modernos): mantém os últimos.
  const slice = keys.slice(-keepLast);
  const next: Record<string, FileContent> = {};
  for (const k of slice) next[k] = contents[k];
  return next;
}

export const useWorkbenchStore = create<WorkbenchState>()(
  immer(
    persist(
      (set, get) => ({
        // ── Shell defaults ──────────────────────────────────────────────────
        byThread: {},
        activeByThread: {},
        panelOpen: {},
        activeTabByThread: {},
        splitSize: 40,
        pinnedFiles: {},
        pending: {},

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
                activeByThread: {
                  ...s.activeByThread,
                  [threadId]: instance.id,
                },
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
              activeTabByThread: {
                ...s.activeTabByThread,
                [threadId]: "terminal",
              },
            };
          }),

        close: (threadId, id) =>
          set((s) => {
            const filtered = (s.byThread[threadId] ?? []).filter(
              (t) => t.id !== id,
            );
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
          set((s) => ({
            activeByThread: { ...s.activeByThread, [threadId]: id },
          })),

        togglePanel: (threadId) =>
          set((s) => ({
            panelOpen: { ...s.panelOpen, [threadId]: !s.panelOpen[threadId] },
          })),

        setPanelOpen: (threadId, open) =>
          set((s) => ({ panelOpen: { ...s.panelOpen, [threadId]: open } })),

        getActiveTab: (threadId) =>
          get().activeTabByThread[threadId] ?? "terminal",
        setActiveTab: (threadId, tab) =>
          set((s) => ({
            activeTabByThread: { ...s.activeTabByThread, [threadId]: tab },
            panelOpen: { ...s.panelOpen, [threadId]: true },
          })),

        setSplitSize: (size) => set({ splitSize: size }),

        togglePinned: (threadId, path) =>
          set((s) => {
            const cur = s.pinnedFiles[threadId] ?? [];
            const next = cur.includes(path)
              ? cur.filter((p) => p !== path)
              : [...cur, path];
            return { pinnedFiles: { ...s.pinnedFiles, [threadId]: next } };
          }),
        isPinned: (threadId, path) =>
          (get().pinnedFiles[threadId] ?? []).includes(path),

        // ── Caches voláteis ─────────────────────────────────────────────────
        files: {},
        diff: {},
        plan: {},

        getFiles: (wsId) => get().files[wsId] ?? EMPTY_FILES,
        setFilesEntries: (wsId, path, entries) =>
          set((s) => {
            const cur = s.files[wsId] ?? EMPTY_FILES;
            return {
              files: {
                ...s.files,
                [wsId]: {
                  ...cur,
                  entriesByDir: { ...cur.entriesByDir, [path]: entries },
                  fetchedAt: { ...cur.fetchedAt, [path]: Date.now() },
                },
              },
            };
          }),
        toggleExpanded: (wsId, path) =>
          set((s) => {
            const cur = s.files[wsId] ?? EMPTY_FILES;
            const expanded = cur.expandedDirs.includes(path)
              ? cur.expandedDirs.filter((p) => p !== path)
              : [...cur.expandedDirs, path];
            return {
              files: { ...s.files, [wsId]: { ...cur, expandedDirs: expanded } },
            };
          }),
        setOpenFile: (wsId, path) =>
          set((s) => {
            const cur = s.files[wsId] ?? EMPTY_FILES;
            return {
              files: { ...s.files, [wsId]: { ...cur, openPath: path } },
            };
          }),
        setFileContent: (wsId, path, content) =>
          set((s) => {
            const cur = s.files[wsId] ?? EMPTY_FILES;
            const nextContents = pruneContents({
              ...cur.contents,
              [path]: content,
            });
            return {
              files: {
                ...s.files,
                [wsId]: { ...cur, contents: nextContents },
              },
            };
          }),
        setFilesFilter: (wsId, filter) =>
          set((s) => {
            const cur = s.files[wsId] ?? EMPTY_FILES;
            return { files: { ...s.files, [wsId]: { ...cur, filter } } };
          }),
        invalidateFiles: (wsId) =>
          set((s) => {
            if (!wsId) return { files: {} };
            const cur = s.files[wsId];
            if (!cur) return s;
            return {
              files: { ...s.files, [wsId]: { ...cur, fetchedAt: {} } },
            };
          }),

        getDiff: (wsId) => get().diff[wsId] ?? EMPTY_DIFF,
        setDiffSummary: (wsId, summary) =>
          set((s) => {
            const cur = s.diff[wsId] ?? EMPTY_DIFF;
            return {
              diff: {
                ...s.diff,
                [wsId]: {
                  ...cur,
                  summary,
                  summaryFetchedAt: Date.now(),
                },
              },
            };
          }),
        setDiffOpenFile: (wsId, path, open) =>
          set((s) => {
            const cur = s.diff[wsId] ?? EMPTY_DIFF;
            const next = open
              ? [...new Set([...cur.openFiles, path])]
              : cur.openFiles.filter((p) => p !== path);
            return { diff: { ...s.diff, [wsId]: { ...cur, openFiles: next } } };
          }),
        setDiffHunks: (wsId, path, hunks) =>
          set((s) => {
            const cur = s.diff[wsId] ?? EMPTY_DIFF;
            return {
              diff: {
                ...s.diff,
                [wsId]: {
                  ...cur,
                  hunksByFile: { ...cur.hunksByFile, [path]: hunks },
                  fileFetchedAt: { ...cur.fileFetchedAt, [path]: Date.now() },
                },
              },
            };
          }),
        invalidateDiff: (wsId) =>
          set((s) => {
            if (!wsId) return { diff: {} };
            const cur = s.diff[wsId];
            if (!cur) return s;
            return {
              diff: {
                ...s.diff,
                [wsId]: { ...cur, summaryFetchedAt: 0, fileFetchedAt: {} },
              },
            };
          }),

        getPlan: (threadId) => get().plan[threadId] ?? EMPTY_PLAN,
        setPlanItems: (threadId, items) =>
          set((s) => {
            const cur = s.plan[threadId] ?? EMPTY_PLAN;
            return {
              plan: {
                ...s.plan,
                [threadId]: { ...cur, items, fetchedAt: Date.now() },
              },
            };
          }),
        setPlanOpenSlug: (threadId, slug) =>
          set((s) => {
            const cur = s.plan[threadId] ?? EMPTY_PLAN;
            return {
              plan: { ...s.plan, [threadId]: { ...cur, openSlug: slug } },
            };
          }),
        setPlanContent: (threadId, slug, content) =>
          set((s) => {
            const cur = s.plan[threadId] ?? EMPTY_PLAN;
            return {
              plan: {
                ...s.plan,
                [threadId]: {
                  ...cur,
                  contentsBySlug: { ...cur.contentsBySlug, [slug]: content },
                },
              },
            };
          }),
        invalidatePlan: (threadId) =>
          set((s) => {
            if (!threadId) return { plan: {} };
            const cur = s.plan[threadId];
            if (!cur) return s;
            return {
              plan: { ...s.plan, [threadId]: { ...cur, fetchedAt: 0 } },
            };
          }),

        markPending: (wsId) =>
          set((s) => ({
            pending: { ...s.pending, [wsId]: { files: true, diff: true } },
          })),
        clearPending: (wsId, key) =>
          set((s) => {
            const cur = s.pending[wsId];
            if (!cur || !cur[key]) return s;
            return {
              pending: { ...s.pending, [wsId]: { ...cur, [key]: false } },
            };
          }),
      }),
      {
        name: "vectora-workbench",
        storage: createJSONStorage(() =>
          typeof window !== "undefined"
            ? localStorage
            : {
                getItem: () => null,
                setItem: () => {},
                removeItem: () => {},
              },
        ),
        // Apenas o "shell" persiste. Caches voláteis (files/diff/plan) ficam
        // de fora — são revalidados rápido e a verdade vive no backend.
        partialize: (state) => ({
          byThread: state.byThread,
          activeByThread: state.activeByThread,
          panelOpen: state.panelOpen,
          activeTabByThread: state.activeTabByThread,
          splitSize: state.splitSize,
          pinnedFiles: state.pinnedFiles,
        }),
      },
    ),
  ),
);

// ── Retro-compat (T3) ─────────────────────────────────────────────────────
// Mantém o nome legado para componentes que ainda não migraram.
export const useTerminalsStore = useWorkbenchStore;

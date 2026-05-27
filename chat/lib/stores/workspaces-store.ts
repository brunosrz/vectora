/**
 * Workspaces Store — Zustand (G1)
 *
 * Cache client-side da lista de workspaces e do workspace ativo.
 * Padrão stale-while-revalidate: exibe cache imediatamente e revalida
 * em background.
 */

import { create } from "zustand";

export interface WorkspaceInfo {
  id: string;
  name: string;
  cwd: string;
  created_at: string;
  /** true se o cwd contém um repositório git (G7) */
  is_git_repo: boolean;
  git_remote: string | null;
  git_current_branch: string | null;
  git_default_branch: string | null;
  bucket_names: string[];
  manifest_version: number;
}

interface WorkspacesState {
  /** Lista de workspaces conhecidos (cache). */
  workspaces: WorkspaceInfo[];
  /** ID do workspace ativo (null = não carregado ainda). */
  active_id: string | null;
  /** Timestamp da última busca bem-sucedida. */
  fetchedAt: number | null;
  /** true enquanto está buscando. */
  loading: boolean;

  // ── Reads ─────────────────────────────────────────────────────────────────
  getActive: () => WorkspaceInfo | null;
  getById: (id: string) => WorkspaceInfo | null;

  // ── Writes ────────────────────────────────────────────────────────────────
  setWorkspaces: (list: WorkspaceInfo[], activeId: string | null) => void;
  setActive: (id: string) => void;
  setLoading: (v: boolean) => void;
  invalidate: () => void;
}

export const useWorkspacesStore = create<WorkspacesState>((set, get) => ({
  workspaces: [],
  active_id: null,
  fetchedAt: null,
  loading: false,

  getActive: () => {
    const { workspaces, active_id } = get();
    if (!active_id) return workspaces[0] ?? null;
    return workspaces.find((w) => w.id === active_id) ?? workspaces[0] ?? null;
  },

  getById: (id) => get().workspaces.find((w) => w.id === id) ?? null,

  setWorkspaces: (list, activeId) =>
    set({ workspaces: list, active_id: activeId, fetchedAt: Date.now() }),

  setActive: (id) => set({ active_id: id }),

  setLoading: (v) => set({ loading: v }),

  invalidate: () => set({ fetchedAt: null }),
}));

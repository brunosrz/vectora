/**
 * Workspaces Store — Zustand (G1, Q6)
 *
 * Cache client-side da lista de workspaces e do workspace ativo.
 * Padrão stale-while-revalidate: exibe cache imediatamente e revalida
 * em background. Ações async conversam com o proxy Hono em /api/workspaces.
 */

import { create } from "zustand";

export interface WorkspaceInfo {
  id: string;
  name: string;
  cwd: string;
  /** true quando o usuário confiou na pasta — libera write/terminal/git */
  trusted: boolean;
  /** true se o cwd contém um repositório git */
  is_git_repo: boolean;
  git_remote: string | null;
  git_current_branch: string | null;
  git_default_branch: string | null;
}

export interface DirEntry {
  name: string;
  path: string;
  is_dir: boolean;
}

export interface BrowseResult {
  path: string;
  parent: string | null;
  entries: DirEntry[];
  /** ID da safe-root que cobre o path atual; null quando privilegiado
   *  navegando livre. Espelha o backend (F.3.2). */
  safe_root_id?: string | null;
}

/** Resumo de uma safe-root para o painel de acesso rápido (F.3.5). */
export interface SafeRootSummary {
  id: string;
  path: string;
  label: string;
  builtin: boolean;
}

interface WorkspacesState {
  workspaces: WorkspaceInfo[];
  active_id: string | null;
  fetchedAt: number | null;
  loading: boolean;
  safeRoots: SafeRootSummary[];

  // ── Reads ─────────────────────────────────────────────────────────────────
  getActive: () => WorkspaceInfo | null;
  getById: (id: string) => WorkspaceInfo | null;

  // ── Local writes ────────────────────────────────────────────────────────────
  setWorkspaces: (list: WorkspaceInfo[], activeId: string | null) => void;
  setLoading: (v: boolean) => void;
  invalidate: () => void;

  // ── Async (proxy Hono) ──────────────────────────────────────────────────────
  hydrate: () => Promise<void>;
  setActive: (id: string) => Promise<void>;
  create: (
    path: string,
    opts?: { trust?: boolean; git_init?: boolean },
  ) => Promise<WorkspaceInfo | null>;
  trust: (id: string) => Promise<WorkspaceInfo | null>;
  gitInit: (id: string) => Promise<WorkspaceInfo | null>;
  browse: (path?: string) => Promise<BrowseResult | null>;
  /** Carrega safe-roots visíveis para o usuário atual (F.3.5). */
  loadSafeRoots: () => Promise<void>;
}

async function fetchJson(url: string, init?: RequestInit): Promise<any | null> {
  try {
    const res = await fetch(url, init);
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export const useWorkspacesStore = create<WorkspacesState>((set, get) => ({
  workspaces: [],
  active_id: null,
  fetchedAt: null,
  loading: false,
  safeRoots: [],

  getActive: () => {
    const { workspaces, active_id } = get();
    if (!active_id) return workspaces[0] ?? null;
    return workspaces.find((w) => w.id === active_id) ?? workspaces[0] ?? null;
  },

  getById: (id) => get().workspaces.find((w) => w.id === id) ?? null,

  setWorkspaces: (list, activeId) =>
    set({ workspaces: list, active_id: activeId, fetchedAt: Date.now() }),

  setLoading: (v) => set({ loading: v }),

  invalidate: () => set({ fetchedAt: null }),

  hydrate: async () => {
    set({ loading: true });
    const data = await fetchJson("/api/workspaces");
    if (data?.workspaces) {
      set({
        workspaces: data.workspaces,
        active_id: data.active_id ?? null,
        fetchedAt: Date.now(),
      });
    }
    set({ loading: false });
  },

  setActive: async (id) => {
    set({ active_id: id });
    await fetchJson("/api/workspaces/set-active", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ workspace_id: id }),
    });
  },

  create: async (path, opts) => {
    const data = await fetchJson("/api/workspaces/create", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        path,
        trust: opts?.trust ?? false,
        git_init: opts?.git_init ?? false,
      }),
    });
    if (data?.status === "ok" && data.workspace) {
      await get().hydrate();
      set({ active_id: data.workspace.id });
      return data.workspace as WorkspaceInfo;
    }
    return null;
  },

  trust: async (id) => {
    const data = await fetchJson("/api/workspaces/trust", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ workspace_id: id }),
    });
    if (data?.status === "ok" && data.workspace) {
      set((s) => ({
        workspaces: s.workspaces.map((w) => (w.id === id ? data.workspace : w)),
      }));
      return data.workspace as WorkspaceInfo;
    }
    return null;
  },

  gitInit: async (id) => {
    const data = await fetchJson("/api/workspaces/git-init", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ workspace_id: id }),
    });
    if (data?.status === "ok" && data.workspace) {
      set((s) => ({
        workspaces: s.workspaces.map((w) => (w.id === id ? data.workspace : w)),
      }));
      return data.workspace as WorkspaceInfo;
    }
    return null;
  },

  browse: async (path) => {
    const q = path ? `?path=${encodeURIComponent(path)}` : "";
    const data = await fetchJson(`/api/workspaces/browse${q}`);
    if (data?.path !== undefined) return data as BrowseResult;
    return null;
  },

  loadSafeRoots: async () => {
    const data = await fetchJson("/api/workspaces/safe-roots");
    if (data?.roots && Array.isArray(data.roots)) {
      set({ safeRoots: data.roots as SafeRootSummary[] });
    }
  },
}));

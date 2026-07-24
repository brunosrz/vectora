import { create } from "zustand";

/**
 * library-store — cache compartilhado dos 3 catálogos da aba Library
 * (MCP/Skills/Memory), sobrevivendo ao unmount do AccordionContent do Radix
 * (que desmonta a seção inteira ao fechar o item). Sem isso, fechar e reabrir
 * qualquer seção refaz o fetch do zero mesmo com dado ainda fresco.
 */

export interface MCPConnector {
  id: string;
  name: string;
  description: string;
  install_cmd: string;
  env_vars: string[];
  homepage: string;
  category: string;
  vectora_verified: boolean;
  icon_url?: string | null;
}

export interface CatalogSkill {
  id: string;
  name: string;
  description: string;
  source: string;
}

export interface MemoryBucket {
  id: string;
  name: string;
  description: string;
  embed_model: string;
  verified: boolean;
  downloads_count: number;
  license?: string;
}

const TTL_MS = 5 * 60 * 1000;

async function fetchMcpRegistry(): Promise<MCPConnector[]> {
  const res = await fetch("/mcp/registry");
  if (!res.ok) return [];
  return res.json();
}

async function fetchMcpInstalledIds(): Promise<Set<string>> {
  const res = await fetch("/plugins");
  if (!res.ok) return new Set();
  const data = (await res.json()) as { servers?: { name: string }[] };
  return new Set((data.servers ?? []).map((s) => s.name));
}

async function fetchSkillsCatalog(): Promise<CatalogSkill[]> {
  const res = await fetch("/skills/catalog");
  if (!res.ok) return [];
  const data = (await res.json()) as { entries?: CatalogSkill[] };
  return data.entries ?? [];
}

async function fetchMemoryCatalog(): Promise<MemoryBucket[]> {
  const res = await fetch("/rag-library/catalog");
  if (!res.ok) return [];
  return res.json();
}

interface LibraryStoreState {
  mcpItems: MCPConnector[];
  mcpInstalledIds: Set<string>;
  mcpLoading: boolean;
  mcpFetchedAt: number | null;

  skillsItems: CatalogSkill[];
  skillsLoading: boolean;
  skillsFetchedAt: number | null;

  memoryItems: MemoryBucket[];
  memoryLoading: boolean;
  memoryFetchedAt: number | null;

  ensureMcpLoaded: () => Promise<void>;
  invalidateMcp: () => void;
  ensureSkillsLoaded: () => Promise<void>;
  invalidateSkills: () => void;
  ensureMemoryLoaded: () => Promise<void>;
  invalidateMemory: () => void;
}

function isFresh(fetchedAt: number | null): boolean {
  return fetchedAt !== null && Date.now() - fetchedAt < TTL_MS;
}

export const useLibraryStore = create<LibraryStoreState>((set, get) => ({
  mcpItems: [],
  mcpInstalledIds: new Set(),
  mcpLoading: false,
  mcpFetchedAt: null,

  skillsItems: [],
  skillsLoading: false,
  skillsFetchedAt: null,

  memoryItems: [],
  memoryLoading: false,
  memoryFetchedAt: null,

  ensureMcpLoaded: async () => {
    const s = get();
    if (s.mcpLoading || isFresh(s.mcpFetchedAt)) return;
    set({ mcpLoading: true });
    try {
      const [items, installedIds] = await Promise.all([
        fetchMcpRegistry(),
        fetchMcpInstalledIds(),
      ]);
      set({
        mcpItems: items,
        mcpInstalledIds: installedIds,
        mcpFetchedAt: Date.now(),
      });
    } finally {
      set({ mcpLoading: false });
    }
  },

  invalidateMcp: () => set({ mcpFetchedAt: null }),

  ensureSkillsLoaded: async () => {
    const s = get();
    if (s.skillsLoading || isFresh(s.skillsFetchedAt)) return;
    set({ skillsLoading: true });
    try {
      const items = await fetchSkillsCatalog();
      set({ skillsItems: items, skillsFetchedAt: Date.now() });
    } finally {
      set({ skillsLoading: false });
    }
  },

  invalidateSkills: () => set({ skillsFetchedAt: null }),

  ensureMemoryLoaded: async () => {
    const s = get();
    if (s.memoryLoading || isFresh(s.memoryFetchedAt)) return;
    set({ memoryLoading: true });
    try {
      const items = await fetchMemoryCatalog();
      set({ memoryItems: items, memoryFetchedAt: Date.now() });
    } finally {
      set({ memoryLoading: false });
    }
  },

  invalidateMemory: () => set({ memoryFetchedAt: null }),
}));

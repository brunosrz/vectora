/**
 * TDD — Bloco T (T5+T11): workbench-store
 *
 * Cobre:
 * - Shell (terminais, painel, aba ativa, split, pins) — persistido.
 * - Slices voláteis Files/Diff/Plan — sobrevivem a remount, não a reload.
 * - Invalidate por SSE (zera fetchedAt sem apagar conteúdo).
 * - Referências estáveis (EMPTY_*) — não causam infinite loop.
 *
 * O teste reseta o store entre casos via `setState({...defaults})` para
 * isolar (Zustand é singleton por módulo).
 */

import { describe, it, expect, beforeEach } from "vitest";
import {
  useWorkbenchStore,
  WORKBENCH_TABS,
  type TerminalInstance,
} from "../lib/stores/workbench-store";

function reset() {
  useWorkbenchStore.setState({
    byThread: {},
    activeByThread: {},
    panelOpen: {},
    activeTabByThread: {},
    splitSize: 40,
    pinnedFiles: {},
    files: {},
    diff: {},
    plan: {},
  });
}

beforeEach(reset);

// ---------------------------------------------------------------------------
// WORKBENCH_TABS — constante exportada
// ---------------------------------------------------------------------------

describe("WORKBENCH_TABS", () => {
  it("expõe as 4 abas na ordem da UI", () => {
    expect(WORKBENCH_TABS).toEqual(["terminal", "files", "diff", "plan"]);
  });
});

// ---------------------------------------------------------------------------
// Shell — terminais
// ---------------------------------------------------------------------------

describe("workbench-store: terminais (shell)", () => {
  const inst: TerminalInstance = {
    id: "t1",
    title: "shell",
    workspaceId: "ws-a",
  };

  it("list() devolve EMPTY_LIST estável quando thread não tem terminais", () => {
    const s = useWorkbenchStore.getState();
    const a = s.list("thread-X");
    const b = s.list("thread-X");
    expect(a).toEqual([]);
    // Mesma referência → não causa re-render em useSyncExternalStore.
    expect(a).toBe(b);
  });

  it("open() adiciona terminal e marca panel aberto + aba terminal", () => {
    useWorkbenchStore.getState().open("thread-1", inst);
    const s = useWorkbenchStore.getState();
    expect(s.list("thread-1")).toEqual([inst]);
    expect(s.isOpen("thread-1")).toBe(true);
    expect(s.getActiveTab("thread-1")).toBe("terminal");
    expect(s.active("thread-1")).toEqual(inst);
  });

  it("open() do mesmo id é idempotente — não duplica", () => {
    useWorkbenchStore.getState().open("thread-1", inst);
    useWorkbenchStore.getState().open("thread-1", inst);
    expect(useWorkbenchStore.getState().list("thread-1")).toHaveLength(1);
  });

  it("close() remove e re-aponta active para o próximo terminal", () => {
    const a = { id: "a", title: "a", workspaceId: "ws" };
    const b = { id: "b", title: "b", workspaceId: "ws" };
    useWorkbenchStore.getState().open("thread-1", a);
    useWorkbenchStore.getState().open("thread-1", b);
    useWorkbenchStore.getState().setActive("thread-1", "b");

    useWorkbenchStore.getState().close("thread-1", "b");
    const s = useWorkbenchStore.getState();
    expect(s.list("thread-1")).toEqual([a]);
    expect(s.active("thread-1")?.id).toBe("a");
  });

  it("togglePanel() inverte o estado por thread", () => {
    const t = useWorkbenchStore.getState().togglePanel;
    t("th");
    expect(useWorkbenchStore.getState().isOpen("th")).toBe(true);
    t("th");
    expect(useWorkbenchStore.getState().isOpen("th")).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// Shell — aba ativa, split, pins
// ---------------------------------------------------------------------------

describe("workbench-store: shell extra", () => {
  it("setActiveTab() troca a aba e abre o painel", () => {
    useWorkbenchStore.getState().setActiveTab("th", "files");
    const s = useWorkbenchStore.getState();
    expect(s.getActiveTab("th")).toBe("files");
    expect(s.isOpen("th")).toBe(true);
  });

  it("getActiveTab() default é 'terminal'", () => {
    expect(useWorkbenchStore.getState().getActiveTab("never-seen")).toBe(
      "terminal",
    );
  });

  it("setSplitSize() persiste tamanho do painel", () => {
    useWorkbenchStore.getState().setSplitSize(55);
    expect(useWorkbenchStore.getState().splitSize).toBe(55);
  });

  it("togglePinned() alterna pin de arquivo", () => {
    const { togglePinned, isPinned } = useWorkbenchStore.getState();
    togglePinned("th", "src/main.ts");
    expect(isPinned("th", "src/main.ts")).toBe(true);
    togglePinned("th", "src/main.ts");
    expect(isPinned("th", "src/main.ts")).toBe(false);
  });

  it("pins são isolados por thread", () => {
    const { togglePinned, isPinned } = useWorkbenchStore.getState();
    togglePinned("a", "x.md");
    expect(isPinned("a", "x.md")).toBe(true);
    expect(isPinned("b", "x.md")).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// Files slice
// ---------------------------------------------------------------------------

describe("workbench-store: files slice", () => {
  it("getFiles() devolve cache vazio estável para workspace novo", () => {
    const a = useWorkbenchStore.getState().getFiles("ws-X");
    const b = useWorkbenchStore.getState().getFiles("ws-X");
    expect(a.expandedDirs).toEqual([]);
    expect(a.entriesByDir).toEqual({});
    expect(a.openPath).toBeNull();
    // Mesma referência — não dispara re-render.
    expect(a).toBe(b);
  });

  it("setFilesEntries() popula entriesByDir e marca fetchedAt", () => {
    const before = Date.now();
    useWorkbenchStore
      .getState()
      .setFilesEntries("ws", "src", [
        { name: "main.ts", path: "src/main.ts", kind: "file" },
      ]);
    const cache = useWorkbenchStore.getState().getFiles("ws");
    expect(cache.entriesByDir["src"]).toHaveLength(1);
    expect(cache.fetchedAt["src"]).toBeGreaterThanOrEqual(before);
  });

  it("toggleExpanded() alterna pasta na lista", () => {
    const { toggleExpanded } = useWorkbenchStore.getState();
    toggleExpanded("ws", "src");
    expect(useWorkbenchStore.getState().getFiles("ws").expandedDirs).toContain(
      "src",
    );
    toggleExpanded("ws", "src");
    expect(
      useWorkbenchStore.getState().getFiles("ws").expandedDirs,
    ).not.toContain("src");
  });

  it("setOpenFile() / setFileContent() — viewer e conteúdo", () => {
    useWorkbenchStore.getState().setOpenFile("ws", "README.md");
    useWorkbenchStore.getState().setFileContent("ws", "README.md", {
      path: "README.md",
      kind: "text",
      content: "# Hi",
      size: 4,
    });
    const cache = useWorkbenchStore.getState().getFiles("ws");
    expect(cache.openPath).toBe("README.md");
    expect(cache.contents["README.md"]?.content).toBe("# Hi");
  });

  it("LRU: mantém apenas os últimos 8 conteúdos", () => {
    const { setFileContent } = useWorkbenchStore.getState();
    for (let i = 0; i < 12; i++) {
      setFileContent("ws", `file${i}.md`, {
        path: `file${i}.md`,
        kind: "text",
        content: String(i),
        size: 1,
      });
    }
    const cache = useWorkbenchStore.getState().getFiles("ws");
    const keys = Object.keys(cache.contents);
    expect(keys).toHaveLength(8);
    // Os 8 últimos (file4..file11) ficaram
    expect(keys).toContain("file11.md");
    expect(keys).toContain("file4.md");
    expect(keys).not.toContain("file0.md");
  });

  it("setFilesFilter() preserva entriesByDir (não invalida)", () => {
    useWorkbenchStore
      .getState()
      .setFilesEntries("ws", "src", [
        { name: "x.ts", path: "src/x.ts", kind: "file" },
      ]);
    useWorkbenchStore.getState().setFilesFilter("ws", "main");
    const cache = useWorkbenchStore.getState().getFiles("ws");
    expect(cache.filter).toBe("main");
    expect(cache.entriesByDir["src"]).toHaveLength(1);
  });

  it("invalidateFiles(wsId) zera fetchedAt mas mantém estrutura", () => {
    const { setFilesEntries, invalidateFiles } = useWorkbenchStore.getState();
    setFilesEntries("ws", "src", []);
    invalidateFiles("ws");
    const cache = useWorkbenchStore.getState().getFiles("ws");
    // Estrutura ainda existe (caller verá entries vazias mas isStale=true).
    expect(cache.fetchedAt).toEqual({});
  });

  it("invalidateFiles() sem arg zera todos os workspaces", () => {
    const { setFilesEntries, invalidateFiles } = useWorkbenchStore.getState();
    setFilesEntries("ws-a", "", []);
    setFilesEntries("ws-b", "", []);
    invalidateFiles();
    expect(useWorkbenchStore.getState().files).toEqual({});
  });
});

// ---------------------------------------------------------------------------
// Diff slice
// ---------------------------------------------------------------------------

describe("workbench-store: diff slice", () => {
  it("getDiff() devolve cache vazio estável", () => {
    const a = useWorkbenchStore.getState().getDiff("ws");
    const b = useWorkbenchStore.getState().getDiff("ws");
    expect(a.summary).toBeNull();
    expect(a).toBe(b);
  });

  it("setDiffSummary() popula resumo + timestamp", () => {
    const before = Date.now();
    useWorkbenchStore.getState().setDiffSummary("ws", {
      is_git_repo: true,
      total_additions: 5,
      total_deletions: 2,
      files: [],
    });
    const cache = useWorkbenchStore.getState().getDiff("ws");
    expect(cache.summary?.total_additions).toBe(5);
    expect(cache.summaryFetchedAt).toBeGreaterThanOrEqual(before);
  });

  it("setDiffOpenFile() add/remove arquivo aberto sem duplicar", () => {
    const { setDiffOpenFile } = useWorkbenchStore.getState();
    setDiffOpenFile("ws", "x.md", true);
    setDiffOpenFile("ws", "x.md", true); // idempotente
    expect(useWorkbenchStore.getState().getDiff("ws").openFiles).toEqual([
      "x.md",
    ]);
    setDiffOpenFile("ws", "x.md", false);
    expect(useWorkbenchStore.getState().getDiff("ws").openFiles).toEqual([]);
  });

  it("setDiffHunks() armazena hunks por path", () => {
    useWorkbenchStore
      .getState()
      .setDiffHunks("ws", "x.md", [{ header: "@@", lines: ["+a"] }]);
    expect(
      useWorkbenchStore.getState().getDiff("ws").hunksByFile["x.md"],
    ).toHaveLength(1);
  });

  it("invalidateDiff(wsId) zera timestamps sem apagar summary", () => {
    const { setDiffSummary, invalidateDiff } = useWorkbenchStore.getState();
    setDiffSummary("ws", {
      is_git_repo: true,
      total_additions: 0,
      total_deletions: 0,
      files: [],
    });
    invalidateDiff("ws");
    const cache = useWorkbenchStore.getState().getDiff("ws");
    expect(cache.summaryFetchedAt).toBe(0);
    expect(cache.fileFetchedAt).toEqual({});
  });
});

// ---------------------------------------------------------------------------
// Plan slice
// ---------------------------------------------------------------------------

describe("workbench-store: plan slice", () => {
  it("getPlan() devolve cache vazio estável", () => {
    const a = useWorkbenchStore.getState().getPlan("th");
    const b = useWorkbenchStore.getState().getPlan("th");
    expect(a.items).toEqual([]);
    expect(a.openSlug).toBeNull();
    expect(a).toBe(b);
  });

  it("setPlanItems() popula lista e timestamp", () => {
    const before = Date.now();
    useWorkbenchStore.getState().setPlanItems("th", [
      {
        title: "Plano A",
        path: "/a.md",
        session_id: "th",
        created_at: "2025",
      },
    ]);
    const cache = useWorkbenchStore.getState().getPlan("th");
    expect(cache.items).toHaveLength(1);
    expect(cache.fetchedAt).toBeGreaterThanOrEqual(before);
  });

  it("setPlanOpenSlug() / setPlanContent() — viewer e conteúdo", () => {
    useWorkbenchStore.getState().setPlanOpenSlug("th", "plano-a");
    useWorkbenchStore.getState().setPlanContent("th", "plano-a", "# Plano A");
    const cache = useWorkbenchStore.getState().getPlan("th");
    expect(cache.openSlug).toBe("plano-a");
    expect(cache.contentsBySlug["plano-a"]).toBe("# Plano A");
  });

  it("invalidatePlan(threadId) zera fetchedAt", () => {
    const { setPlanItems, invalidatePlan } = useWorkbenchStore.getState();
    setPlanItems("th", []);
    invalidatePlan("th");
    expect(useWorkbenchStore.getState().getPlan("th").fetchedAt).toBe(0);
  });
});

// ---------------------------------------------------------------------------
// Isolamento por thread / workspace
// ---------------------------------------------------------------------------

describe("workbench-store: isolamento", () => {
  it("dois workspaces têm caches files independentes", () => {
    useWorkbenchStore
      .getState()
      .setFilesEntries("ws-a", "", [
        { name: "a.md", path: "a.md", kind: "file" },
      ]);
    expect(useWorkbenchStore.getState().getFiles("ws-b").entriesByDir).toEqual(
      {},
    );
  });

  it("duas threads têm planos independentes", () => {
    useWorkbenchStore.getState().setPlanItems("th-1", [
      {
        title: "P1",
        path: "/p1.md",
        session_id: "th-1",
        created_at: "2025",
      },
    ]);
    expect(useWorkbenchStore.getState().getPlan("th-2").items).toEqual([]);
  });
});

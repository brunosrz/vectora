/**
 * Tests para o `library-store`: cache TTL entre unmount/remount das seções
 * da aba Library (o bug real era refetch a cada fechar/reabrir accordion).
 */

import { describe, expect, it, beforeEach, vi } from "vitest";
import { useLibraryStore } from "../library-store";

function resetStore() {
  useLibraryStore.setState({
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
  });
}

beforeEach(() => {
  resetStore();
  vi.restoreAllMocks();
});

describe("library-store — MCP", () => {
  it("ensureMcpLoaded busca registry+instalados na primeira chamada", async () => {
    const fetchMock = vi.fn(async (url: string) => {
      if (String(url).includes("/mcp/registry")) {
        return {
          ok: true,
          json: async () => [{ id: "a", name: "A" } as never],
        } as Response;
      }
      return {
        ok: true,
        json: async () => ({ servers: [{ name: "a" }] }),
      } as Response;
    });
    vi.stubGlobal("fetch", fetchMock);

    await useLibraryStore.getState().ensureMcpLoaded();

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(useLibraryStore.getState().mcpItems).toHaveLength(1);
    expect(useLibraryStore.getState().mcpInstalledIds.has("a")).toBe(true);
  });

  it("dentro do TTL, chamada repetida não refaz fetch (fix do bug de refetch ao reabrir)", async () => {
    const fetchMock = vi.fn(async () => ({
      ok: true,
      json: async () => [],
    })) as unknown as typeof fetch;
    vi.stubGlobal("fetch", fetchMock);

    await useLibraryStore.getState().ensureMcpLoaded();
    const callsAfterFirst = (fetchMock as ReturnType<typeof vi.fn>).mock.calls
      .length;
    await useLibraryStore.getState().ensureMcpLoaded();

    expect((fetchMock as ReturnType<typeof vi.fn>).mock.calls.length).toBe(
      callsAfterFirst,
    );
  });

  it("erro/borda: fetch expirado (fetchedAt antigo) refaz a busca", async () => {
    const fetchMock = vi.fn(async () => ({
      ok: true,
      json: async () => [],
    })) as unknown as typeof fetch;
    vi.stubGlobal("fetch", fetchMock);

    await useLibraryStore.getState().ensureMcpLoaded();
    useLibraryStore.setState({ mcpFetchedAt: Date.now() - 10 * 60 * 1000 });
    await useLibraryStore.getState().ensureMcpLoaded();

    expect(
      (fetchMock as ReturnType<typeof vi.fn>).mock.calls.length,
    ).toBeGreaterThan(2);
  });

  it("invalidateMcp força refetch na próxima chamada", async () => {
    const fetchMock = vi.fn(async () => ({
      ok: true,
      json: async () => [],
    })) as unknown as typeof fetch;
    vi.stubGlobal("fetch", fetchMock);

    await useLibraryStore.getState().ensureMcpLoaded();
    useLibraryStore.getState().invalidateMcp();
    await useLibraryStore.getState().ensureMcpLoaded();

    expect(
      (fetchMock as ReturnType<typeof vi.fn>).mock.calls.length,
    ).toBeGreaterThan(2);
  });
});

describe("library-store — Skills e Memory", () => {
  it("ensureSkillsLoaded popula skillsItems e não refetch dentro do TTL", async () => {
    const fetchMock = vi.fn(async () => ({
      ok: true,
      json: async () => ({ entries: [{ id: "s1", name: "Skill" }] }),
    })) as unknown as typeof fetch;
    vi.stubGlobal("fetch", fetchMock);

    await useLibraryStore.getState().ensureSkillsLoaded();
    await useLibraryStore.getState().ensureSkillsLoaded();

    expect(useLibraryStore.getState().skillsItems).toHaveLength(1);
    expect((fetchMock as ReturnType<typeof vi.fn>).mock.calls.length).toBe(1);
  });

  it("erro/borda: resposta não-ok em skills não lança e deixa lista vazia", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({ ok: false, json: async () => ({}) })),
    );

    await expect(
      useLibraryStore.getState().ensureSkillsLoaded(),
    ).resolves.not.toThrow();
    expect(useLibraryStore.getState().skillsItems).toEqual([]);
  });

  it("ensureMemoryLoaded popula memoryItems e não refetch dentro do TTL", async () => {
    const fetchMock = vi.fn(async () => ({
      ok: true,
      json: async () => [{ id: "m1", name: "Bucket" }],
    })) as unknown as typeof fetch;
    vi.stubGlobal("fetch", fetchMock);

    await useLibraryStore.getState().ensureMemoryLoaded();
    await useLibraryStore.getState().ensureMemoryLoaded();

    expect(useLibraryStore.getState().memoryItems).toHaveLength(1);
    expect((fetchMock as ReturnType<typeof vi.fn>).mock.calls.length).toBe(1);
  });
});

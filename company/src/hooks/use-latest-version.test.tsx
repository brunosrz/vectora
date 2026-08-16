// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";

import { useLatestVersion } from "./use-latest-version";

function makeWrapper() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return {
    qc,
    wrapper: ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={qc}>{children}</QueryClientProvider>
    ),
  };
}

const fetchMock = vi.fn();

beforeEach(() => {
  fetchMock.mockReset();
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("useLatestVersion", () => {
  it("resolve a versão do canal 'latest' por padrão", async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      json: async () => ({ version: "0.1.10", channel: "latest" }),
    });
    const { wrapper } = makeWrapper();

    const { result } = renderHook(() => useLatestVersion(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toBe("0.1.10");
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/version/latest"),
    );
  });

  it("canal customizado é repassado na URL", async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      json: async () => ({ version: "0.1.11-beta", channel: "beta" }),
    });
    const { wrapper } = makeWrapper();

    const { result } = renderHook(() => useLatestVersion("beta"), {
      wrapper,
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/version/beta"),
    );
  });

  it("resposta não-ok (API fora do ar) resolve null, não lança", async () => {
    fetchMock.mockResolvedValue({ ok: false, json: async () => ({}) });
    const { wrapper } = makeWrapper();

    const { result } = renderHook(() => useLatestVersion(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toBeNull();
  });

  it("erro de rede vira estado de erro do hook, sem derrubar o componente", async () => {
    fetchMock.mockRejectedValue(new Error("network down"));
    const { wrapper } = makeWrapper();

    const { result } = renderHook(() => useLatestVersion(), { wrapper });

    // retry: 1 do hook soma um round-trip extra antes de isError virar true.
    await waitFor(() => expect(result.current.isError).toBe(true), {
      timeout: 3000,
    });
    expect(result.current.data).toBeUndefined();
  });
});

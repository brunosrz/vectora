// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";

import {
  useApiKeys,
  useCreateApiKey,
  useRevokeApiKey,
  API_KEYS_QUERY_KEY,
} from "./use-api-keys";

const { mockListApiKeys, mockCreateApiKey, mockRevokeApiKey } = vi.hoisted(
  () => ({
    mockListApiKeys: vi.fn(),
    mockCreateApiKey: vi.fn(),
    mockRevokeApiKey: vi.fn(),
  }),
);

vi.mock("#/server/fns/api-keys", () => ({
  listApiKeys: mockListApiKeys,
  createApiKey: mockCreateApiKey,
  revokeApiKey: mockRevokeApiKey,
}));

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

beforeEach(() => {
  vi.clearAllMocks();
});

describe("useApiKeys", () => {
  it("expõe a lista de chaves", async () => {
    mockListApiKeys.mockResolvedValue([{ id: "k1", name: "CI" }]);
    const { wrapper } = makeWrapper();

    const { result } = renderHook(() => useApiKeys(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toHaveLength(1);
  });
});

describe("useCreateApiKey", () => {
  it("invalida a lista de chaves após criar", async () => {
    mockCreateApiKey.mockResolvedValue({ secret: "sk_new" });
    const { wrapper, qc } = makeWrapper();
    const invalidateSpy = vi.spyOn(qc, "invalidateQueries");

    const { result } = renderHook(() => useCreateApiKey(), { wrapper });

    await act(async () => {
      await result.current.mutateAsync({ name: "Deploy", scopes: ["read"] });
    });

    expect(mockCreateApiKey).toHaveBeenCalledWith({
      data: { name: "Deploy", scopes: ["read"] },
    });
    expect(invalidateSpy).toHaveBeenCalledWith(
      expect.objectContaining({ queryKey: API_KEYS_QUERY_KEY }),
    );
  });
});

describe("useRevokeApiKey", () => {
  it("invalida a lista de chaves após revogar", async () => {
    mockRevokeApiKey.mockResolvedValue({ ok: true });
    const { wrapper, qc } = makeWrapper();
    const invalidateSpy = vi.spyOn(qc, "invalidateQueries");

    const { result } = renderHook(() => useRevokeApiKey(), { wrapper });

    await act(async () => {
      await result.current.mutateAsync("k1");
    });

    expect(mockRevokeApiKey).toHaveBeenCalledWith({ data: { id: "k1" } });
    expect(invalidateSpy).toHaveBeenCalledWith(
      expect.objectContaining({ queryKey: API_KEYS_QUERY_KEY }),
    );
  });

  it("não invalida a lista quando a revogação falha (edge)", async () => {
    mockRevokeApiKey.mockRejectedValue(new Error("services_error_404"));
    const { wrapper, qc } = makeWrapper();
    const invalidateSpy = vi.spyOn(qc, "invalidateQueries");

    const { result } = renderHook(() => useRevokeApiKey(), { wrapper });

    await act(async () => {
      await expect(result.current.mutateAsync("ghost-id")).rejects.toThrow();
    });

    expect(invalidateSpy).not.toHaveBeenCalled();
  });
});

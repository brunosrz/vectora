// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";

import { useSession, SESSION_QUERY_KEY } from "./use-session";

const { mockGetSession } = vi.hoisted(() => ({ mockGetSession: vi.fn() }));

vi.mock("#/server/fns/auth", () => ({ getSession: mockGetSession }));

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("useSession", () => {
  it("expõe o usuário autenticado após resolver", async () => {
    mockGetSession.mockResolvedValue({ id: "u1", email: "a@b.com" });

    const { result } = renderHook(() => useSession(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual({ id: "u1", email: "a@b.com" });
  });

  it("expõe null quando não há sessão (edge — visitante anônimo)", async () => {
    mockGetSession.mockResolvedValue(null);

    const { result } = renderHook(() => useSession(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toBeNull();
  });

  it("usa a query key esperada", () => {
    expect(SESSION_QUERY_KEY).toEqual(["session"]);
  });
});

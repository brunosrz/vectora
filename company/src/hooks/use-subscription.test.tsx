// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";

import {
  useSubscription,
  useLicenseHistory,
  useCreateCheckout,
  useCreatePortal,
} from "./use-subscription";

const {
  mockGetSubscription,
  mockCreateCheckout,
  mockCreatePortal,
  mockGetLicenseHistory,
} = vi.hoisted(() => ({
  mockGetSubscription: vi.fn(),
  mockCreateCheckout: vi.fn(),
  mockCreatePortal: vi.fn(),
  mockGetLicenseHistory: vi.fn(),
}));

vi.mock("#/server/fns/subscription", () => ({
  getSubscription: mockGetSubscription,
  createCheckout: mockCreateCheckout,
  createPortal: mockCreatePortal,
  getLicenseHistory: mockGetLicenseHistory,
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

const originalLocation = window.location;

beforeEach(() => {
  vi.clearAllMocks();
  Object.defineProperty(window, "location", {
    configurable: true,
    value: { ...originalLocation, href: "" },
  });
});

afterEach(() => {
  Object.defineProperty(window, "location", {
    configurable: true,
    value: originalLocation,
  });
});

describe("useSubscription", () => {
  it("expõe a assinatura carregada", async () => {
    mockGetSubscription.mockResolvedValue({ tier: "pro" });
    const { wrapper } = makeWrapper();

    const { result } = renderHook(() => useSubscription(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual({ tier: "pro" });
  });
});

describe("useLicenseHistory", () => {
  it("expõe o histórico de validações", async () => {
    mockGetLicenseHistory.mockResolvedValue([{ id: "1" }]);
    const { wrapper } = makeWrapper();

    const { result } = renderHook(() => useLicenseHistory(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toHaveLength(1);
  });
});

describe("useCreateCheckout", () => {
  it("redireciona para a URL de checkout ao suceder", async () => {
    mockCreateCheckout.mockResolvedValue({ url: "https://checkout.test/x" });
    const { wrapper } = makeWrapper();

    const { result } = renderHook(() => useCreateCheckout(), { wrapper });

    await act(async () => {
      await result.current.mutateAsync({ planId: "1m" });
    });

    expect(window.location.href).toBe("https://checkout.test/x");
    expect(mockCreateCheckout).toHaveBeenCalledWith({
      data: { planId: "1m" },
    });
  });

  it("um cupom free_lifetime (redeemed: true) não tenta redirecionar (edge)", async () => {
    mockCreateCheckout.mockResolvedValue({ redeemed: true });
    const { wrapper } = makeWrapper();

    const { result } = renderHook(() => useCreateCheckout(), { wrapper });

    await act(async () => {
      await result.current.mutateAsync({ planId: "1m", couponCode: "SECRET" });
    });

    expect(window.location.href).toBe("");
  });
});

describe("useCreatePortal", () => {
  it("invalida a query de assinatura e redireciona para o portal", async () => {
    mockCreatePortal.mockResolvedValue({ url: "https://portal.test/x" });
    const { wrapper, qc } = makeWrapper();
    const invalidateSpy = vi.spyOn(qc, "invalidateQueries");

    const { result } = renderHook(() => useCreatePortal(), { wrapper });

    await act(async () => {
      await result.current.mutateAsync();
    });

    expect(invalidateSpy).toHaveBeenCalledWith(
      expect.objectContaining({ queryKey: ["subscription"] }),
    );
    expect(window.location.href).toBe("https://portal.test/x");
  });
});

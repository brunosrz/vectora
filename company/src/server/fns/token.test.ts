import { describe, it, expect, vi, beforeEach } from "vitest";

import { getTokenStatus, getToken, rotateToken } from "./token";

const { mockServicesFetch } = vi.hoisted(() => ({
  mockServicesFetch: vi.fn(),
}));

vi.mock("#/lib/services/client", () => ({
  servicesFetch: mockServicesFetch,
}));

beforeEach(() => {
  vi.clearAllMocks();
});

describe("getTokenStatus", () => {
  it("retorna available=true quando há um token recuperável", async () => {
    mockServicesFetch.mockResolvedValue({ available: true });
    await expect(getTokenStatus()).resolves.toEqual({ available: true });
  });

  it("retorna available=false quando a conta não tem token recuperável (edge)", async () => {
    mockServicesFetch.mockResolvedValue({ available: false });
    await expect(getTokenStatus()).resolves.toEqual({ available: false });
  });
});

describe("getToken", () => {
  it("retorna o token em texto plano — recuperável, não show-once", async () => {
    mockServicesFetch.mockResolvedValue({ token: "vct_abc123" });

    const result = await getToken();

    expect(result).toEqual({ token: "vct_abc123" });
  });
});

describe("rotateToken", () => {
  it("retorna o novo token gerado", async () => {
    mockServicesFetch.mockResolvedValue({ token: "vct_rotated456" });

    await expect(rotateToken()).resolves.toEqual({ token: "vct_rotated456" });
    expect(mockServicesFetch).toHaveBeenCalledWith(
      "/license/rotate",
      expect.objectContaining({ method: "POST" }),
    );
  });
});

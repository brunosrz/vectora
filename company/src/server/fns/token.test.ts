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
  it("retorna revealed=true quando já foi revelado antes", async () => {
    mockServicesFetch.mockResolvedValue({ revealed: true });
    await expect(getTokenStatus()).resolves.toEqual({ revealed: true });
  });

  it("retorna revealed=false na primeira visita (edge)", async () => {
    mockServicesFetch.mockResolvedValue({ revealed: false });
    await expect(getTokenStatus()).resolves.toEqual({ revealed: false });
  });
});

describe("getToken", () => {
  it("retorna o token em texto plano na primeira revelação", async () => {
    mockServicesFetch.mockResolvedValue({
      revealed: false,
      token: "vct_abc123",
    });

    const result = await getToken();

    expect(result).toEqual({ revealed: false, token: "vct_abc123" });
  });

  it("retorna token=null quando já foi revelado antes (edge — show-once)", async () => {
    mockServicesFetch.mockResolvedValue({ revealed: true, token: null });

    const result = await getToken();

    expect(result.token).toBeNull();
    expect(result.revealed).toBe(true);
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

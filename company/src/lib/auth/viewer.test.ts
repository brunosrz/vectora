import { describe, it, expect, vi, beforeEach } from "vitest";

import { resolveViewerRole } from "./viewer";

const { mockGetSession } = vi.hoisted(() => ({
  mockGetSession: vi.fn(),
}));

vi.mock("#/server/fns/auth", () => ({
  getSession: mockGetSession,
}));

beforeEach(() => {
  vi.clearAllMocks();
});

describe("resolveViewerRole", () => {
  it("isAdmin: true quando a sessão tem role admin", async () => {
    mockGetSession.mockResolvedValue({ role: "admin" });
    await expect(resolveViewerRole()).resolves.toEqual({ isAdmin: true });
  });

  it("isAdmin: false pra usuário comum, sem sessão, e se getSession lançar (fail-safe)", async () => {
    mockGetSession.mockResolvedValue({ role: "user" });
    await expect(resolveViewerRole()).resolves.toEqual({ isAdmin: false });

    mockGetSession.mockResolvedValue(null);
    await expect(resolveViewerRole()).resolves.toEqual({ isAdmin: false });

    mockGetSession.mockRejectedValue(new Error("network down"));
    await expect(resolveViewerRole()).resolves.toEqual({ isAdmin: false });
  });
});

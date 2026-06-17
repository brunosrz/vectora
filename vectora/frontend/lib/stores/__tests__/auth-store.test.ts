/**
 * Tests para o auth-store: setUser/clearUser e hydrate (200, 401+refresh,
 * offline). Tokens nunca tocam o store (ficam em cookies httpOnly).
 */

import { describe, expect, it, beforeEach, afterEach, vi } from "vitest";
import { useAuthStore } from "../auth-store";
import type { AuthUser } from "@/lib/types/auth";

const USER = { id: "u1", email: "a@b.com" } as unknown as AuthUser;

function jsonRes(body: unknown, ok = true, status = 200): Response {
  return {
    ok,
    status,
    json: async () => body,
  } as unknown as Response;
}

beforeEach(() => {
  useAuthStore.setState({ user: null, isAuthenticated: false });
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("auth-store — síncrono", () => {
  it("setUser define user e isAuthenticated", () => {
    useAuthStore.getState().setUser(USER);
    expect(useAuthStore.getState().user).toEqual(USER);
    expect(useAuthStore.getState().isAuthenticated).toBe(true);
  });

  it("clearUser zera a sessão local", () => {
    useAuthStore.getState().setUser(USER);
    useAuthStore.getState().clearUser();
    expect(useAuthStore.getState().user).toBeNull();
    expect(useAuthStore.getState().isAuthenticated).toBe(false);
  });
});

describe("auth-store — hydrate", () => {
  it("200 em /auth/me autentica", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => jsonRes(USER)),
    );
    await useAuthStore.getState().hydrate();
    expect(useAuthStore.getState().isAuthenticated).toBe(true);
    expect(useAuthStore.getState().user).toEqual(USER);
  });

  it("401 → refresh ok → /auth/me ok autentica", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonRes(null, false, 401)) // /auth/me
      .mockResolvedValueOnce(jsonRes({}, true)) // /auth/refresh
      .mockResolvedValueOnce(jsonRes(USER, true)); // /auth/me de novo
    vi.stubGlobal("fetch", fetchMock);
    await useAuthStore.getState().hydrate();
    expect(useAuthStore.getState().isAuthenticated).toBe(true);
  });

  it("401 → refresh falha → limpa a sessão", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonRes(null, false, 401))
      .mockResolvedValueOnce(jsonRes(null, false, 401));
    vi.stubGlobal("fetch", fetchMock);
    useAuthStore.getState().setUser(USER);
    await useAuthStore.getState().hydrate();
    expect(useAuthStore.getState().isAuthenticated).toBe(false);
  });

  it("backend offline preserva o estado anterior", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new Error("network down");
      }),
    );
    useAuthStore.getState().setUser(USER);
    await useAuthStore.getState().hydrate();
    // Não muda nada — cache anterior continua válido.
    expect(useAuthStore.getState().isAuthenticated).toBe(true);
  });
});

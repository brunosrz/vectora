// @vitest-environment jsdom
/**
 * Testes para `ensureAuthenticated` (guard de auth do `beforeLoad` da rota
 * raiz) — cobre o fix da causa-raiz do wizard/settings sumindo no modo
 * Free: antes, com `auth_required=false`, a função retornava sem nunca
 * buscar `/auth/me`, deixando o auth-store vazio.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const { redirectSpy } = vi.hoisted(() => ({
  redirectSpy: vi.fn((opts: { to: string }) => {
    throw { ...opts, __isRedirect: true };
  }),
}));

vi.mock("@tanstack/react-router", () => ({
  Outlet: () => null,
  useLocation: () => ({ pathname: "/" }),
  createRootRouteWithContext: () => (opts: unknown) => opts,
  redirect: redirectSpy,
}));

import { useAuthStore } from "@/lib/stores/auth-store";
import { ensureAuthenticated } from "../__root";

function jsonRes(body: unknown, ok = true, status = 200): Response {
  return { ok, status, json: async () => body } as unknown as Response;
}

function flagsRes(authRequired: boolean): Response {
  return jsonRes({ auth_required: authRequired });
}

const VIRTUAL_LOCAL_USER = {
  id: "local",
  email: "local@vectora.internal",
  role: "root",
  name: "Bruno",
};

beforeEach(() => {
  useAuthStore.setState({ user: null, isAuthenticated: false });
  redirectSpy.mockClear();
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("ensureAuthenticated — path público", () => {
  it("retorna sem nenhum fetch para /auth/*, /share/* e /onboarding", async () => {
    const fetchSpy = vi.fn();
    vi.stubGlobal("fetch", fetchSpy);

    await ensureAuthenticated("/auth/signin");
    await ensureAuthenticated("/share/abc");
    await ensureAuthenticated("/onboarding");

    expect(fetchSpy).not.toHaveBeenCalled();
  });
});

describe("ensureAuthenticated — auth_required=false (modo Free)", () => {
  it("nunca chama /auth/has-users e popula o store via /auth/me (fix da causa-raiz)", async () => {
    const calledUrls: string[] = [];
    const fetchSpy = vi.fn(async (url: string) => {
      calledUrls.push(url);
      if (url === "/settings/flags") return flagsRes(false);
      if (url === "/auth/me") return jsonRes(VIRTUAL_LOCAL_USER);
      throw new Error(`unexpected fetch: ${url}`);
    });
    vi.stubGlobal("fetch", fetchSpy);

    await ensureAuthenticated("/");

    expect(calledUrls).not.toContain("/auth/has-users");
    expect(calledUrls).toContain("/auth/me");
    expect(useAuthStore.getState().user).toEqual(VIRTUAL_LOCAL_USER);
    expect(useAuthStore.getState().isAuthenticated).toBe(true);
    expect(redirectSpy).not.toHaveBeenCalled();
  });

  it("não força redirect pro signin mesmo se /auth/me falhar (Free nunca exige login)", async () => {
    const fetchSpy = vi.fn(async (url: string) => {
      if (url === "/settings/flags") return flagsRes(false);
      if (url === "/auth/me") throw new Error("offline");
      throw new Error(`unexpected fetch: ${url}`);
    });
    vi.stubGlobal("fetch", fetchSpy);

    await expect(ensureAuthenticated("/")).resolves.toBeUndefined();
    expect(redirectSpy).not.toHaveBeenCalled();
    expect(useAuthStore.getState().user).toBeNull();
  });
});

describe("ensureAuthenticated — auth_required=true (primeiro acesso / Pro)", () => {
  it("has-users=false redireciona pro /onboarding", async () => {
    const fetchSpy = vi.fn(async (url: string) => {
      if (url === "/settings/flags") return flagsRes(true);
      if (url === "/auth/has-users") return jsonRes({ exists: false });
      throw new Error(`unexpected fetch: ${url}`);
    });
    vi.stubGlobal("fetch", fetchSpy);

    await expect(ensureAuthenticated("/")).rejects.toMatchObject({
      to: "/onboarding",
    });
    expect(redirectSpy).toHaveBeenCalledWith({ to: "/onboarding" });
  });

  it("/auth/me falhando redireciona pro /auth/signin (par de erro)", async () => {
    const fetchSpy = vi.fn(async (url: string) => {
      if (url === "/settings/flags") return flagsRes(true);
      if (url === "/auth/has-users") return jsonRes({ exists: true });
      if (url === "/auth/me") throw new Error("offline");
      throw new Error(`unexpected fetch: ${url}`);
    });
    vi.stubGlobal("fetch", fetchSpy);

    await expect(ensureAuthenticated("/session/abc")).rejects.toMatchObject({
      to: "/auth/signin",
    });
    expect(useAuthStore.getState().user).toBeNull();
  });

  it("200 em /auth/me autentica normalmente", async () => {
    const proUser = { id: "u1", email: "a@b.com", role: "member" };
    const fetchSpy = vi.fn(async (url: string) => {
      if (url === "/settings/flags") return flagsRes(true);
      if (url === "/auth/has-users") return jsonRes({ exists: true });
      if (url === "/auth/me") return jsonRes(proUser);
      throw new Error(`unexpected fetch: ${url}`);
    });
    vi.stubGlobal("fetch", fetchSpy);

    await ensureAuthenticated("/");

    expect(useAuthStore.getState().user).toEqual(proUser);
    expect(useAuthStore.getState().isAuthenticated).toBe(true);
    expect(redirectSpy).not.toHaveBeenCalled();
  });
});

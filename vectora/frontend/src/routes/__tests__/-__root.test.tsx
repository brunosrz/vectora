// @vitest-environment jsdom
/**
 * Testes para `ensureAuthenticated` (guard de auth do `beforeLoad` da rota
 * raiz) — cobre o fix da causa-raiz do wizard/settings sumindo no modo
 * Free: antes, com `auth_required=false`, a função retornava sem nunca
 * buscar `/auth/me`, deixando o auth-store vazio.
 */

import type { ComponentType } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, cleanup } from "@testing-library/react";

const { redirectSpy, currentPathname } = vi.hoisted(() => ({
  redirectSpy: vi.fn((opts: { to: string }) => {
    throw { ...opts, __isRedirect: true };
  }),
  currentPathname: { value: "/" },
}));

vi.mock("@tanstack/react-router", () => ({
  Outlet: () => null,
  useLocation: () => ({ pathname: currentPathname.value }),
  createRootRouteWithContext: () => (opts: unknown) => opts,
  redirect: redirectSpy,
}));

// TitleBar/NetworkStatusBanner/Toaster puxam bridges/contexto irrelevantes
// pro teste do hydrate de workspaces — stubs simples.
vi.mock("@/components/layout/title-bar", () => ({ TitleBar: () => null }));
vi.mock("@/components/layout/network-status-banner", () => ({
  NetworkStatusBanner: () => null,
}));
vi.mock("@/components/ui/toaster", () => ({ Toaster: () => null }));

import { useAuthStore } from "@/lib/stores/auth-store";
import { useWorkspacesStore } from "@/lib/stores/workspaces-store";
import { ensureAuthenticated, Route } from "../__root";

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
  currentPathname.value = "/";
  useWorkspacesStore.setState({ workspaces: [], active_id: null });
  // RootComponent reage a `prefers-color-scheme` quando o tema é "system"
  // (default) — jsdom não implementa matchMedia.
  window.matchMedia =
    window.matchMedia ??
    ((query: string) =>
      ({
        matches: false,
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      }) as unknown as MediaQueryList);
});

afterEach(() => {
  cleanup();
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

// ============================================================================
// RootComponent — hydrate de workspaces (fix da sidebar caindo no
// agrupamento por data em vez da árvore por workspace)
// ============================================================================
describe("RootComponent — hydrate de workspaces", () => {
  it("hidrata workspaces ao montar numa rota protegida", async () => {
    const hydrateSpy = vi
      .spyOn(useWorkspacesStore.getState(), "hydrate")
      .mockResolvedValue(undefined);
    currentPathname.value = "/session/abc";

    const Component = (Route as unknown as { component: ComponentType })
      .component;
    render(<Component />);

    expect(hydrateSpy).toHaveBeenCalledTimes(1);
  });

  it("não hidrata em rotas públicas (/auth, /share, /onboarding)", async () => {
    const hydrateSpy = vi
      .spyOn(useWorkspacesStore.getState(), "hydrate")
      .mockResolvedValue(undefined);

    for (const path of ["/auth/signin", "/share/abc", "/onboarding"]) {
      currentPathname.value = path;
      const Component = (Route as unknown as { component: ComponentType })
        .component;
      const { unmount } = render(<Component />);
      unmount();
    }

    expect(hydrateSpy).not.toHaveBeenCalled();
  });

  it("erro: não re-hidrata se workspaces já foram carregados", async () => {
    useWorkspacesStore.setState({
      workspaces: [
        {
          id: "w1",
          name: "vectora",
          cwd: "/home/vectora",
          is_git_repo: true,
        },
      ] as never,
    });
    const hydrateSpy = vi
      .spyOn(useWorkspacesStore.getState(), "hydrate")
      .mockResolvedValue(undefined);
    currentPathname.value = "/session/abc";

    const Component = (Route as unknown as { component: ComponentType })
      .component;
    render(<Component />);

    expect(hydrateSpy).not.toHaveBeenCalled();
  });
});

// @vitest-environment jsdom
/**
 * Testes dos painéis de Administração — cada um exportado direto (não mais
 * atrás de um wrapper `AdminTab` com tab bar própria; ver
 * `settings-categories.test.tsx` pro filtro de tier de "Usuários", que
 * migrou pra `buildSettingsCategoryGroups`).
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  render,
  screen,
  cleanup,
  act,
  fireEvent,
  waitFor,
} from "@testing-library/react";
import { overwriteGetLocale, baseLocale } from "@/lib/paraglide/runtime";

vi.mock("@/lib/hooks/use-license-status", () => ({
  useLicenseStatus: () => ({
    status: { configured: true, tier: "pro" },
    loading: false,
    refetch: vi.fn(),
  }),
}));

const { SystemPanel, SafeRootsPanel } = await import("../admin-tab");

/** Formato mínimo válido pra cada endpoint que os painéis buscam no mount —
 * sem isso `SystemPanel`/`ConfigSection` quebram em campos undefined
 * (ex.: `info.python_version.split(...)`) quando o act() flush deste
 * teste deixa o efeito de fetch assentar de verdade. */
function mockAdminFetch(): void {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => {
      const body: Record<string, unknown> = url.includes("/admin/system")
        ? {
            version: "0.1.0",
            python_version: "3.13.0",
            platform: "test",
            services: {},
            recent_spans_count: 0,
          }
        : url.includes("/admin/config")
          ? {
              default_model: "",
              max_recursion: 50,
              allow_public_signup: false,
              db_dsn: "",
              vectora_token_masked: "",
              vectora_token_configured: false,
            }
          : {};
      return new Response(JSON.stringify(body), { status: 200 });
    }),
  );
}

beforeEach(() => {
  overwriteGetLocale(() => "pt");
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  overwriteGetLocale(() => baseLocale);
});

describe("SystemPanel — Configuração", () => {
  it("não expõe mais modelo padrão nem limite de recursão", async () => {
    // Modelo se escolhe no seletor do chat; recursão é detalhe interno do
    // grafo. Ambos saíram da tela e do payload do PATCH — o teste trava as
    // duas pontas, porque tirar só da tela deixaria o campo sendo enviado.
    mockAdminFetch();

    render(<SystemPanel />);
    await act(async () => {});

    expect(screen.queryByText(/modelo padrão/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/recursão/i)).not.toBeInTheDocument();

    const calls = (global.fetch as unknown as ReturnType<typeof vi.fn>).mock
      .calls as [string, RequestInit | undefined][];
    const patchCall = calls.find(([, init]) => init?.method === "PATCH");
    // Erro/borda: se algum PATCH saiu no mount, ele não pode carregar os
    // campos removidos.
    if (patchCall) {
      const body = JSON.parse(String(patchCall[1]?.body ?? "{}"));
      expect(body).not.toHaveProperty("default_model");
      expect(body).not.toHaveProperty("max_recursion");
    }
  });
});

describe("SafeRootsPanel — seletor nativo de pasta", () => {
  function renderSafeRoots() {
    mockAdminFetch();
    render(<SafeRootsPanel />);
  }

  it("com bridge do desktop: o botão aparece e a pasta escolhida preenche o campo", async () => {
    const pickDirectory = vi.fn(async () => "/home/teste/projetos");
    vi.stubGlobal("vectora", { pickDirectory });

    renderSafeRoots();
    await act(async () => {});

    const browse = screen.getByRole("button", { name: /escolher pasta/i });
    await act(async () => {
      fireEvent.click(browse);
    });

    expect(pickDirectory).toHaveBeenCalled();
    const pathInput = screen.getByPlaceholderText(
      /caminho|path|ruta/i,
    ) as HTMLInputElement;
    await waitFor(() => expect(pathInput.value).toBe("/home/teste/projetos"));
  });

  it("cancelar o diálogo preserva o que já estava digitado", async () => {
    // Erro/borda: `null` é cancelamento. Tratar como valor escolhido
    // apagaria um caminho que o usuário já tinha digitado à mão.
    const pickDirectory = vi.fn(async () => null);
    vi.stubGlobal("vectora", { pickDirectory });

    renderSafeRoots();
    await act(async () => {});

    const input = screen.getByPlaceholderText(
      /\/home\/|caminho|path/i,
    ) as HTMLInputElement;
    fireEvent.change(input, { target: { value: "/tmp/mantido" } });

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /escolher pasta/i }));
    });

    expect(input.value).toBe("/tmp/mantido");
  });

  it("sem bridge (modo web) o botão não renderiza", async () => {
    vi.stubGlobal("vectora", undefined);

    renderSafeRoots();
    await act(async () => {});

    expect(
      screen.queryByRole("button", { name: /escolher pasta/i }),
    ).not.toBeInTheDocument();
  });
});

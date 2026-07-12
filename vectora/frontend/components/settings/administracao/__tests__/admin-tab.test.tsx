// @vitest-environment jsdom
/**
 * Testes para o filtro de abas Free/Pro do AdminTab — a fonte da verdade é
 * `useLicenseStatus()` (mesma que o license-banner usa), não um check
 * improvisado tipo `user.id === "local"`. Free (sem VECTORA_TOKEN
 * configurado) esconde "Usuários" (recurso multi-usuário puro) e nunca
 * pousa nela por padrão.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, cleanup, act } from "@testing-library/react";
import type { LicenseStatus } from "@/lib/hooks/use-license-status";
import { overwriteGetLocale, baseLocale } from "@/lib/paraglide/runtime";

const { useLicenseStatusMock } = vi.hoisted(() => ({
  useLicenseStatusMock: vi.fn(),
}));

vi.mock("@/lib/hooks/use-license-status", () => ({
  useLicenseStatus: useLicenseStatusMock,
}));

const { AdminTab } = await import("../admin-tab");

function licenseStatus(configured: boolean): {
  status: LicenseStatus;
  loading: boolean;
  refetch: () => Promise<void>;
} {
  return {
    status: {
      configured,
      tier: configured ? "pro" : null,
      status: configured ? "active" : "unknown",
      days_remaining: 0,
      expires_at: "",
      cached: false,
    },
    loading: false,
    refetch: vi.fn(),
  };
}

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

describe("AdminTab — filtro de abas por tier", () => {
  it("Free (sem token configurado) esconde a aba Usuários", async () => {
    useLicenseStatusMock.mockReturnValue(licenseStatus(false));
    mockAdminFetch();

    render(<AdminTab />);

    expect(
      screen.queryByRole("button", { name: "Usuários" }),
    ).not.toBeInTheDocument();
    expect(await screen.findByRole("button", { name: "Sistema" })).toHaveClass(
      "border-foreground",
    );
    // Deixa os fetches internos das sub-abas (SystemPanel/ConfigSection)
    // assentarem dentro de act() antes do teste terminar.
    await act(async () => {});
  });

  it("Pro (token configurado) mostra a aba Usuários normalmente", async () => {
    useLicenseStatusMock.mockReturnValue(licenseStatus(true));
    mockAdminFetch();

    render(<AdminTab />);

    expect(
      screen.getByRole("button", { name: "Usuários" }),
    ).toBeInTheDocument();
    await act(async () => {});
  });

  it("durante o loading inicial (status ainda null) não força a aba pra Sistema", async () => {
    // `useLicenseStatus` retorna `status: null` + `loading: true` até o
    // primeiro fetch assentar — `isFree` não pode tratar esse estado como
    // free, senão toda conta (inclusive Pro) pousa em "Sistema" no primeiro
    // render e nunca mais volta pra "Usuários".
    useLicenseStatusMock.mockReturnValue({
      status: null,
      loading: true,
      refetch: vi.fn(),
    });
    mockAdminFetch();

    render(<AdminTab />);

    expect(screen.getByRole("button", { name: "Usuários" })).toHaveClass(
      "border-foreground",
    );
    await act(async () => {});
  });
});

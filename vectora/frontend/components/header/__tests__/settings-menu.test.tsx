// @vitest-environment jsdom
/**
 * Testes para SettingsMenu — cobre o fix da regressão que escondia o botão
 * inteiro sem `isAuthenticated`/`user` (o backend sempre injeta alguém em
 * /auth/me: real no Pro, virtual "local" no Free — ver
 * backend/api/middleware/auth.py::_get_virtual_local_user).
 */

import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen, cleanup, fireEvent } from "@testing-library/react";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn() }),
}));
vi.mock("@/lib/stores/preferencias-dialog-store", () => ({
  usePreferenciasDialogStore: () => vi.fn(),
}));
vi.mock("@/lib/stores/environment-dialog-store", () => ({
  useEnvironmentDialogStore: () => vi.fn(),
}));
vi.mock("@/lib/stores/administracao-dialog-store", () => ({
  useAdministracaoDialogStore: () => vi.fn(),
}));
vi.mock("@/components/settings/settings-overlay", () => ({
  SettingsOverlay: () => null,
}));
vi.mock("@/lib/paraglide/messages", () => ({
  m: {
    settings_group_preferencias: () => "Preferências",
    settings_group_environment: () => "Ambiente",
    settings_group_admin: () => "Administração",
    user_logout: () => "Sair",
  },
}));

const LOCAL_USER = {
  id: "local",
  email: "local@vectora.internal",
  role: "root",
  name: "Bruno",
};

const PRO_USER = {
  id: "u1",
  email: "bruno@example.com",
  role: "member",
  name: "Bruno",
};

async function renderMenu(authState: {
  user: typeof LOCAL_USER | typeof PRO_USER | null;
  isAuthenticated: boolean;
}) {
  vi.doMock("@/lib/stores/auth-store", () => ({
    useAuthStore: () => ({
      ...authState,
      clearUser: vi.fn(),
    }),
  }));
  const { SettingsMenu } = await import("../settings-menu");
  render(<SettingsMenu />);
  fireEvent.click(screen.getByLabelText("Configurações"));
}

afterEach(() => {
  cleanup();
  vi.resetModules();
  vi.restoreAllMocks();
});

describe("SettingsMenu — usuário local virtual (Free, role root)", () => {
  it("botão sempre visível, mostra o nome digitado, Administração visível, Sair ausente", async () => {
    await renderMenu({ user: LOCAL_USER, isAuthenticated: true });

    expect(screen.getByLabelText("Configurações")).toBeInTheDocument();
    expect(screen.getAllByText("Bruno").length).toBeGreaterThan(0);
    expect(screen.getByText("Administração")).toBeInTheDocument();
    expect(screen.queryByText("Sair")).not.toBeInTheDocument();
  });
});

describe("SettingsMenu — conta Pro real", () => {
  it("mostra Administração se role root/admin e Sair sempre visível", async () => {
    await renderMenu({ user: PRO_USER, isAuthenticated: true });

    expect(screen.queryByText("Administração")).not.toBeInTheDocument();
    expect(screen.getByText("Sair")).toBeInTheDocument();
  });

  it("role root também mostra Administração numa conta real", async () => {
    await renderMenu({
      user: { ...PRO_USER, role: "root" },
      isAuthenticated: true,
    });

    expect(screen.getByText("Administração")).toBeInTheDocument();
    expect(screen.getByText("Sair")).toBeInTheDocument();
  });
});

describe("SettingsMenu — sem usuário ainda (guard não resolveu)", () => {
  it("botão continua visível com fallback 'Vectora', sem Administração nem Sair", async () => {
    await renderMenu({ user: null, isAuthenticated: false });

    expect(screen.getByLabelText("Configurações")).toBeInTheDocument();
    expect(screen.getAllByText("Vectora").length).toBeGreaterThan(0);
    expect(screen.queryByText("Administração")).not.toBeInTheDocument();
    expect(screen.queryByText("Sair")).not.toBeInTheDocument();
  });
});

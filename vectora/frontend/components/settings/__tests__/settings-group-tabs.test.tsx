// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";

// ---------------------------------------------------------------------------
// Mock dos stores Zustand — interceta openAt/setOpen sem tocar em estado real
// ---------------------------------------------------------------------------

const mockOpenPref = vi.fn();
const mockClosePref = vi.fn();
const mockOpenEnv = vi.fn();
const mockCloseEnv = vi.fn();
const mockOpenAdmin = vi.fn();
const mockCloseAdmin = vi.fn();

vi.mock("@/lib/stores/preferencias-dialog-store", () => ({
  usePreferenciasDialogStore: (sel: (s: object) => unknown) =>
    sel({
      openAt: mockOpenPref,
      setOpen: mockClosePref,
    }),
}));

vi.mock("@/lib/stores/environment-dialog-store", () => ({
  useEnvironmentDialogStore: (sel: (s: object) => unknown) =>
    sel({
      openAt: mockOpenEnv,
      setOpen: mockCloseEnv,
    }),
}));

vi.mock("@/lib/stores/administracao-dialog-store", () => ({
  useAdministracaoDialogStore: (sel: (s: object) => unknown) =>
    sel({
      openAt: mockOpenAdmin,
      setOpen: mockCloseAdmin,
    }),
}));

vi.mock("@/lib/paraglide/messages", () => ({
  m: new Proxy({}, { get: (_t, prop) => () => String(prop) }),
}));

import { SettingsGroupTabs } from "../settings-group-tabs";

describe("SettingsGroupTabs", () => {
  beforeEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("renderiza os três grupos", () => {
    render(<SettingsGroupTabs active="preferencias" />);
    expect(screen.getByText("settings_group_preferencias")).toBeTruthy();
    expect(screen.getByText("settings_group_environment")).toBeTruthy();
    expect(screen.getByText("settings_group_admin")).toBeTruthy();
  });

  it("grupo ativo tem aria-current=page", () => {
    render(<SettingsGroupTabs active="environment" />);
    const active = screen
      .getAllByRole("button")
      .find((b) => b.getAttribute("aria-current") === "page");
    expect(active?.textContent).toBe("settings_group_environment");
  });

  it("grupos inativos não têm aria-current", () => {
    render(<SettingsGroupTabs active="preferencias" />);
    const withCurrent = screen
      .getAllByRole("button")
      .filter((b) => b.getAttribute("aria-current") === "page");
    expect(withCurrent).toHaveLength(1);
  });

  it("clicar em grupo inativo fecha o atual e abre o target (admin)", () => {
    render(<SettingsGroupTabs active="preferencias" />);
    fireEvent.click(screen.getByText("settings_group_admin"));
    expect(mockClosePref).toHaveBeenCalledWith(false);
    expect(mockCloseEnv).toHaveBeenCalledWith(false);
    expect(mockCloseAdmin).toHaveBeenCalledWith(false);
    expect(mockOpenAdmin).toHaveBeenCalled();
  });

  it("clicar em grupo inativo abre environment", () => {
    render(<SettingsGroupTabs active="admin" />);
    fireEvent.click(screen.getByText("settings_group_environment"));
    expect(mockOpenEnv).toHaveBeenCalled();
    expect(mockOpenAdmin).not.toHaveBeenCalled();
    expect(mockOpenPref).not.toHaveBeenCalled();
  });

  it("clicar no grupo ativo não chama nenhum open", () => {
    render(<SettingsGroupTabs active="preferencias" />);
    fireEvent.click(screen.getByText("settings_group_preferencias"));
    expect(mockOpenPref).not.toHaveBeenCalled();
    expect(mockOpenEnv).not.toHaveBeenCalled();
    expect(mockOpenAdmin).not.toHaveBeenCalled();
  });

  it("container compensa o padding do primeiro botão (px-2) com -ml-2, alinhando o texto com o conteúdo abaixo (Sprint 12)", () => {
    const { container } = render(<SettingsGroupTabs active="preferencias" />);
    const wrapper = container.firstElementChild;
    expect(wrapper?.className).toContain("-ml-2");
  });
});

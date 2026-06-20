// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, cleanup, fireEvent } from "@testing-library/react";

// ── Store mocks ───────────────────────────────────────────────────────────────
// Funções capturadas para verificar chamadas.
const openPref = vi.fn();
const closePref = vi.fn();
const openEnv = vi.fn();
const closeEnv = vi.fn();
const openAdmin = vi.fn();
const closeAdmin = vi.fn();

vi.mock("@/lib/stores/preferencias-dialog-store", () => ({
  usePreferenciasDialogStore: (sel: (s: object) => unknown) =>
    sel({ openAt: openPref, setOpen: closePref }),
}));

vi.mock("@/lib/stores/environment-dialog-store", () => ({
  useEnvironmentDialogStore: (sel: (s: object) => unknown) =>
    sel({ openAt: openEnv, setOpen: closeEnv }),
}));

vi.mock("@/lib/stores/administracao-dialog-store", () => ({
  useAdministracaoDialogStore: (sel: (s: object) => unknown) =>
    sel({ openAt: openAdmin, setOpen: closeAdmin }),
}));

vi.mock("@/lib/paraglide/messages", () => ({
  m: {
    settings_group_preferencias: () => "Preferências",
    settings_group_environment: () => "Ambiente",
    settings_group_admin: () => "Administração",
  },
}));

// ── Subject ───────────────────────────────────────────────────────────────────
import { SettingsGroupTabs } from "../settings-group-tabs";

describe("SettingsGroupTabs", () => {
  beforeEach(() => {
    cleanup();
    openPref.mockClear();
    closePref.mockClear();
    openEnv.mockClear();
    closeEnv.mockClear();
    openAdmin.mockClear();
    closeAdmin.mockClear();
  });

  it("renders the three group buttons", () => {
    render(<SettingsGroupTabs active="preferencias" />);
    expect(screen.getByText("Preferências")).toBeTruthy();
    expect(screen.getByText("Ambiente")).toBeTruthy();
    expect(screen.getByText("Administração")).toBeTruthy();
  });

  it("marks the active group with aria-current=page", () => {
    render(<SettingsGroupTabs active="environment" />);
    const activeBtn = screen.getByText("Ambiente").closest("button");
    expect(activeBtn?.getAttribute("aria-current")).toBe("page");
    const inactiveBtn = screen.getByText("Preferências").closest("button");
    expect(inactiveBtn?.getAttribute("aria-current")).toBeNull();
  });

  it("clicking active group does not trigger store calls", () => {
    render(<SettingsGroupTabs active="preferencias" />);
    fireEvent.click(screen.getByText("Preferências"));
    expect(closePref).not.toHaveBeenCalled();
    expect(openPref).not.toHaveBeenCalled();
  });

  it("clicking environment from preferencias closes pref and opens env", () => {
    render(<SettingsGroupTabs active="preferencias" />);
    fireEvent.click(screen.getByText("Ambiente"));
    expect(closePref).toHaveBeenCalledWith(false);
    expect(closeEnv).toHaveBeenCalledWith(false);
    expect(closeAdmin).toHaveBeenCalledWith(false);
    expect(openEnv).toHaveBeenCalled();
    expect(openPref).not.toHaveBeenCalled();
    expect(openAdmin).not.toHaveBeenCalled();
  });

  it("clicking admin from environment closes env and opens admin", () => {
    render(<SettingsGroupTabs active="environment" />);
    fireEvent.click(screen.getByText("Administração"));
    expect(closeAdmin).toHaveBeenCalledWith(false);
    expect(closeEnv).toHaveBeenCalledWith(false);
    expect(openAdmin).toHaveBeenCalled();
    expect(openEnv).not.toHaveBeenCalled();
  });

  it("clicking preferencias from admin opens preferencias", () => {
    render(<SettingsGroupTabs active="admin" />);
    fireEvent.click(screen.getByText("Preferências"));
    expect(openPref).toHaveBeenCalled();
    expect(openAdmin).not.toHaveBeenCalled();
    expect(openEnv).not.toHaveBeenCalled();
  });
});

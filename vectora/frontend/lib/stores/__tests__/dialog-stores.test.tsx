// @vitest-environment jsdom
/**
 * Tests para os stores de diálogo de configurações (open/openAt/setTab)
 * e o componente SettingsGroupTabs que navega entre eles.
 */

import { describe, expect, it, beforeEach, afterEach, vi } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { useEnvironmentDialogStore } from "../environment-dialog-store";
import { usePreferenciasDialogStore } from "../preferencias-dialog-store";
import { useAdministracaoDialogStore } from "../administracao-dialog-store";

vi.mock("@/lib/paraglide/messages", () => ({
  m: {
    settings_group_preferencias: () => "Preferências",
    settings_group_environment: () => "Ambiente",
    settings_group_admin: () => "Administração",
  },
}));

describe("environment-dialog-store", () => {
  beforeEach(() =>
    useEnvironmentDialogStore.setState({ open: false, tab: "integracoes" }),
  );

  it("openAt abre no tab pedido", () => {
    useEnvironmentDialogStore.getState().openAt("plugins");
    expect(useEnvironmentDialogStore.getState().open).toBe(true);
    expect(useEnvironmentDialogStore.getState().tab).toBe("plugins");
  });

  it("openAt sem argumento cai no default 'integracoes'", () => {
    useEnvironmentDialogStore.getState().openAt();
    expect(useEnvironmentDialogStore.getState().tab).toBe("integracoes");
  });

  it("setOpen e setTab atualizam o estado", () => {
    useEnvironmentDialogStore.getState().setTab("integracoes");
    useEnvironmentDialogStore.getState().setOpen(true);
    expect(useEnvironmentDialogStore.getState().tab).toBe("integracoes");
    expect(useEnvironmentDialogStore.getState().open).toBe(true);
  });
});

describe("preferencias-dialog-store", () => {
  beforeEach(() =>
    usePreferenciasDialogStore.setState({ open: false, tab: "preferencias" }),
  );

  it("openAt abre no tab pedido", () => {
    usePreferenciasDialogStore.getState().openAt("memoria");
    expect(usePreferenciasDialogStore.getState().open).toBe(true);
    expect(usePreferenciasDialogStore.getState().tab).toBe("memoria");
  });

  it("openAt sem argumento cai no default 'preferencias'", () => {
    usePreferenciasDialogStore.getState().openAt();
    expect(usePreferenciasDialogStore.getState().tab).toBe("preferencias");
  });
});

describe("administracao-dialog-store", () => {
  beforeEach(() =>
    useAdministracaoDialogStore.setState({ open: false, subTab: undefined }),
  );

  it("openAt abre na sub-aba pedida", () => {
    useAdministracaoDialogStore.getState().openAt("storage");
    expect(useAdministracaoDialogStore.getState().open).toBe(true);
    expect(useAdministracaoDialogStore.getState().subTab).toBe("storage");
  });

  it("setSubTab pode limpar a sub-aba (undefined)", () => {
    useAdministracaoDialogStore.getState().setSubTab("users");
    useAdministracaoDialogStore.getState().setSubTab(undefined);
    expect(useAdministracaoDialogStore.getState().subTab).toBeUndefined();
  });
});

// ── SettingsGroupTabs — integração com os stores ──────────────────────────────

import { SettingsGroupTabs } from "@/components/settings/settings-group-tabs";

function resetStores() {
  usePreferenciasDialogStore.setState({ open: false, tab: "preferencias" });
  useEnvironmentDialogStore.setState({ open: false, tab: "integracoes" });
  useAdministracaoDialogStore.setState({ open: false, subTab: undefined });
}

describe("SettingsGroupTabs", () => {
  beforeEach(resetStores);
  afterEach(cleanup);

  it("renderiza os 3 botões de navegação", () => {
    render(<SettingsGroupTabs active="preferencias" />);
    expect(screen.getAllByRole("button")).toHaveLength(3);
    expect(screen.getByText("Preferências")).toBeTruthy();
    expect(screen.getByText("Ambiente")).toBeTruthy();
    expect(screen.getByText("Administração")).toBeTruthy();
  });

  it("botão do grupo ativo tem aria-current=page", () => {
    render(<SettingsGroupTabs active="environment" />);
    const buttons = screen.getAllByRole("button");
    const active = buttons.find(
      (b) => b.getAttribute("aria-current") === "page",
    );
    expect(active?.textContent).toBe("Ambiente");
    const inactive = buttons.filter(
      (b) => b.getAttribute("aria-current") !== "page",
    );
    expect(inactive).toHaveLength(2);
  });

  it("clicar em grupo inativo fecha o atual e abre o target", () => {
    usePreferenciasDialogStore.setState({ open: true, tab: "preferencias" });
    render(<SettingsGroupTabs active="preferencias" />);

    fireEvent.click(screen.getByText("Ambiente"));

    expect(usePreferenciasDialogStore.getState().open).toBe(false);
    expect(useEnvironmentDialogStore.getState().open).toBe(true);
    expect(useAdministracaoDialogStore.getState().open).toBe(false);
  });

  it("clicar em Administração fecha preferências e abre admin", () => {
    usePreferenciasDialogStore.setState({ open: true, tab: "preferencias" });
    render(<SettingsGroupTabs active="preferencias" />);

    fireEvent.click(screen.getByText("Administração"));

    expect(usePreferenciasDialogStore.getState().open).toBe(false);
    expect(useAdministracaoDialogStore.getState().open).toBe(true);
  });

  it("clicar no grupo ativo não muda estado dos stores", () => {
    usePreferenciasDialogStore.setState({ open: true, tab: "preferencias" });
    render(<SettingsGroupTabs active="preferencias" />);

    fireEvent.click(screen.getByText("Preferências"));

    expect(usePreferenciasDialogStore.getState().open).toBe(true);
    expect(useEnvironmentDialogStore.getState().open).toBe(false);
    expect(useAdministracaoDialogStore.getState().open).toBe(false);
  });
});

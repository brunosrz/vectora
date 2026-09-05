// @vitest-environment jsdom
/**
 * handleThemeChange e handleModeChange controlam campos independentes do
 * store (themePreset vs theme) — trocar um não pode descartar o outro.
 */

import { describe, it, expect, afterEach, beforeEach } from "vitest";
import {
  render,
  screen,
  cleanup,
  fireEvent,
  within,
} from "@testing-library/react";
import { PreferenciasTab } from "../preferencias-tab";
import { useSettingsStore } from "@/lib/stores/settings-store";

afterEach(cleanup);

beforeEach(() => {
  useSettingsStore.setState({ theme: "system", themePreset: "default" });
});

describe("PreferenciasTab — modo e paleta não se contaminam", () => {
  it("selecionar uma paleta (github-dark) em modo 'system' preserva o modo", () => {
    render(<PreferenciasTab />);
    const card = screen.getByText("GitHub Dark").closest("div")!;
    fireEvent.click(card.querySelector("button")!);

    const state = useSettingsStore.getState();
    expect(state.themePreset).toBe("github-dark");
    expect(state.theme).toBe("system");
  });

  it("toggle claro/escuro/sistema fica embutido no cabeçalho da grade (mesma linha do título)", () => {
    render(<PreferenciasTab />);
    const label = screen.getByText(/interface theme/i);
    const header = label.parentElement!;
    expect(within(header).getByRole("group")).toBeInTheDocument();
  });

  it("selecionar o modo 'dark' preserva a paleta ativa (github-dark)", () => {
    useSettingsStore.setState({ theme: "system", themePreset: "github-dark" });
    render(<PreferenciasTab />);
    const modeToggle = within(screen.getAllByRole("group")[0]!);
    fireEvent.click(
      modeToggle.getByRole("button", { name: /^dark$|^escuro$/i }),
    );

    const state = useSettingsStore.getState();
    expect(state.theme).toBe("dark");
    expect(state.themePreset).toBe("github-dark");
  });

  it("selecionar 'system' não descarta uma paleta custom ativa", () => {
    useSettingsStore.setState({ theme: "light", themePreset: "custom" });
    render(<PreferenciasTab />);
    const modeToggle = within(screen.getAllByRole("group")[0]!);
    fireEvent.click(
      modeToggle.getByRole("button", { name: /^system|^sistema/i }),
    );

    const state = useSettingsStore.getState();
    expect(state.theme).toBe("system");
    expect(state.themePreset).toBe("custom");
  });
});

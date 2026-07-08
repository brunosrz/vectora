// @vitest-environment jsdom
/**
 * Testes para os seletores de idioma/tema no primeiro step (identity) do
 * PreAuthWizard — aplicados direto no settings-store, visíveis antes mesmo
 * de escolher o modo local/VPS.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, cleanup, fireEvent } from "@testing-library/react";
import { useSettingsStore } from "@/lib/stores/settings-store";
import { PreAuthWizard } from "../pre-auth-wizard";

vi.mock("@tanstack/react-router", () => ({
  useNavigate: () => vi.fn(),
}));

beforeEach(() => {
  useSettingsStore.setState({ theme: "system", language: "en" });
});

afterEach(() => {
  cleanup();
});

describe("PreAuthWizard — seletores de idioma e tema", () => {
  it("clicar em 'Dark' aplica o tema no settings-store imediatamente", () => {
    render(<PreAuthWizard />);

    fireEvent.click(screen.getByTitle("Dark"));

    expect(useSettingsStore.getState().theme).toBe("dark");
  });

  it("clicar em 'Light' depois de 'Dark' troca o tema (não acumula estado antigo)", () => {
    render(<PreAuthWizard />);

    fireEvent.click(screen.getByTitle("Dark"));
    fireEvent.click(screen.getByTitle("Light"));

    expect(useSettingsStore.getState().theme).toBe("light");
  });

  it("o botão do tema atual reflete aria-pressed=true", () => {
    useSettingsStore.setState({ theme: "dark" });
    render(<PreAuthWizard />);

    expect(screen.getByTitle("Dark")).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByTitle("System")).toHaveAttribute(
      "aria-pressed",
      "false",
    );
  });
});

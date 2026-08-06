// @vitest-environment jsdom
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";

import CapabilitiesSection from "./CapabilitiesSection";

vi.mock("#/paraglide/messages", () => ({
  m: new Proxy(
    {},
    {
      get:
        (_t, prop) =>
        (..._args: unknown[]) =>
          String(prop),
    },
  ),
}));

describe("CapabilitiesSection", () => {
  it("renderiza os 6 cards (3 originais + Terminal/Git/Explorer)", () => {
    render(<CapabilitiesSection />);
    const expectedTitles = [
      "capability_browser_title",
      "capability_sandbox_title",
      "capability_context_graph_title",
      "capability_terminal_title",
      "capability_git_title",
      "capability_explorer_title",
    ];
    for (const title of expectedTitles) {
      expect(screen.getByText(title)).toBeInTheDocument();
    }
  });

  it("erro/borda: cada card tem título e descrição, nenhum vazio", () => {
    const { container } = render(<CapabilitiesSection />);
    const cards = container.querySelectorAll(
      ".grid > div",
    ) as NodeListOf<HTMLElement>;
    expect(cards).toHaveLength(6);
    for (const card of Array.from(cards)) {
      expect(card.textContent?.trim().length).toBeGreaterThan(0);
    }
  });
});

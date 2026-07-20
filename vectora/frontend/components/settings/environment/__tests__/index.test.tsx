// @vitest-environment jsdom
/**
 * EnvironmentDialog — ordem das abas. "Integrações" deve ser a primeira
 * (o usuário reportou testando ao vivo que ela aparecia por último,
 * escondida atrás de Envs/Skills/Plugins/Provider Routing).
 */
import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, cleanup, waitFor } from "@testing-library/react";
import { EnvironmentDialog } from "../index";

vi.mock("@/lib/paraglide/messages", () => ({
  m: new Proxy(
    {},
    {
      get:
        (_t, prop) =>
        (...args: unknown[]) =>
          args.length
            ? `${String(prop)}(${JSON.stringify(args[0])})`
            : String(prop),
    },
  ),
}));

vi.mock("@/lib/stores/environment-dialog-store", () => ({
  useEnvironmentDialogStore: (
    sel: (s: {
      open: boolean;
      tab: string;
      setOpen: () => void;
      setTab: () => void;
    }) => unknown,
  ) => sel({ open: true, tab: "envs", setOpen: vi.fn(), setTab: vi.fn() }),
}));

vi.mock("../tabs/envs-tab", () => ({ EnvsTab: () => <div>envs-content</div> }));
vi.mock("../tabs/skills-tab", () => ({
  SkillsTab: () => <div>skills-content</div>,
}));
vi.mock("../tabs/plugins-tab", () => ({
  PluginsTab: () => <div>plugins-content</div>,
}));
vi.mock("../tabs/provider-routing-tab", () => ({
  ProviderRoutingTab: () => <div>provider-routing-content</div>,
}));
vi.mock("../tabs/integracoes-tab", () => ({
  IntegracoesTab: () => <div>integracoes-content</div>,
}));

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("EnvironmentDialog", () => {
  it("mostra Integrações como a primeira aba, antes de Envs/Skills/Plugins/Provider Routing", async () => {
    render(<EnvironmentDialog />);

    await waitFor(() => {
      expect(screen.getAllByRole("tab").length).toBeGreaterThan(0);
    });

    const labels = screen.getAllByRole("tab").map((el) => el.textContent);
    expect(labels[0]).toBe("Integrações");
    expect(labels).toEqual([
      "Integrações",
      "Envs",
      "Skills",
      "Plugins",
      "Provider Routing",
    ]);
  });
});

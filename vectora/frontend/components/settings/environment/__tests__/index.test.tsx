// @vitest-environment jsdom
/**
 * EnvironmentDialog — ordem das abas. "Integrações" deve ser a primeira.
 * O dialog só cobre Integrações e Provider Routing; Skills e Plugins vivem
 * na Library (workbench).
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
  ) =>
    sel({ open: true, tab: "integracoes", setOpen: vi.fn(), setTab: vi.fn() }),
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
  it("mostra Integrações como a primeira aba, antes de Provider Routing", async () => {
    render(<EnvironmentDialog />);

    await waitFor(() => {
      expect(screen.getAllByRole("tab").length).toBeGreaterThan(0);
    });

    const labels = screen.getAllByRole("tab").map((el) => el.textContent);
    expect(labels[0]).toBe("Integrações");
    expect(labels).toEqual(["Integrações", "Provider Routing"]);
  });

  it("barra de sub-abas compensa o px-3 do TabsTrigger com -ml-3, alinhando o texto com o conteúdo abaixo", async () => {
    render(<EnvironmentDialog />);

    await waitFor(() => {
      expect(screen.getAllByRole("tab").length).toBeGreaterThan(0);
    });

    const tabsList = screen.getAllByRole("tab")[0].closest('[role="tablist"]');
    expect(tabsList?.className).toContain("-ml-3");
  });
});

// @vitest-environment jsdom
/**
 * PreferenciasDialog — alinhamento da barra de sub-abas (Sprint 12).
 */
import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, cleanup, waitFor } from "@testing-library/react";
import { PreferenciasDialog } from "../index";

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

vi.mock("@/lib/stores/preferencias-dialog-store", () => ({
  usePreferenciasDialogStore: (
    sel: (s: {
      open: boolean;
      tab: string;
      setOpen: () => void;
      setTab: () => void;
    }) => unknown,
  ) =>
    sel({ open: true, tab: "preferencias", setOpen: vi.fn(), setTab: vi.fn() }),
}));

vi.mock("../tabs/preferencias-tab", () => ({
  PreferenciasTab: () => <div>preferencias-content</div>,
}));
vi.mock("../tabs/memoria-tab", () => ({
  MemoriaTab: () => <div>memoria-content</div>,
}));
vi.mock("../tabs/conta-tab", () => ({
  ContaTab: () => <div>conta-content</div>,
}));

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("PreferenciasDialog", () => {
  it("barra de sub-abas compensa o px-3 do TabsTrigger com -ml-3, alinhando o texto com o conteúdo abaixo (Sprint 12)", async () => {
    render(<PreferenciasDialog />);

    await waitFor(() => {
      expect(screen.getAllByRole("tab").length).toBeGreaterThan(0);
    });

    const tabsList = screen.getAllByRole("tab")[0].closest('[role="tablist"]');
    expect(tabsList?.className).toContain("-ml-3");
  });
});

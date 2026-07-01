// @vitest-environment jsdom
/**
 * WorkbenchNavBar — gating de BETA_TABS via enableFeaturesBeta.
 *
 * Cobre: ComingSoonTabButton (toast ao clicar), NavTabButton para tabs normais,
 * e a alternância entre os dois com base na feature flag.
 */

import { describe, it, expect, vi, afterEach, beforeEach } from "vitest";
import { render, screen, cleanup, fireEvent } from "@testing-library/react";

// ── mocks ────────────────────────────────────────────────────────────────────

const mockPush = vi.fn();
vi.mock("@/lib/stores/toast-store", () => ({
  useToastStore: { getState: () => ({ push: mockPush }) },
}));

const mockSelectTab = vi.fn();
vi.mock("@/lib/stores/workbench-store", () => ({
  WORKBENCH_TABS: ["files", "context_graph", "terminal"],
  useWorkbenchStore: (sel: (s: object) => unknown) =>
    sel({
      getActiveTab: () => "files",
      isOpen: () => true,
      selectTab: mockSelectTab,
      list: () => [],
      pinnedFiles: {},
      getPlan: () => ({ items: [] }),
      pending: {},
    }),
}));

vi.mock("@/lib/stores/workspaces-store", () => ({
  useWorkspacesStore: (sel: (s: object) => unknown) =>
    sel({ getActive: () => null }),
}));

vi.mock("@/lib/hooks/use-hydrated", () => ({ useHydrated: () => true }));
vi.mock("@/lib/hooks/use-workspace-watcher", () => ({
  useWorkspaceWatcher: () => undefined,
}));

let featuresBeta = false;
vi.mock("@/lib/hooks/use-feature-flags", () => ({
  useFeatureFlags: () => ({ enableFeaturesBeta: featuresBeta }),
}));

vi.mock("@/lib/paraglide/messages", () => ({
  m: new Proxy(
    {},
    {
      get: (_t, prop) => () => String(prop),
    },
  ),
}));
vi.mock("@/lib/i18n-dyn", () => ({
  mDyn: (key: string) => key,
}));
vi.mock("@/components/ui/tooltip", () => ({
  Tooltip: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  TooltipTrigger: ({
    children,
    asChild,
  }: {
    children: React.ReactNode;
    asChild?: boolean;
  }) => {
    void asChild;
    return <>{children}</>;
  },
  TooltipContent: ({ children }: { children: React.ReactNode }) => (
    <span data-tooltip>{children}</span>
  ),
}));

import { WorkbenchNavBar, WorkbenchContent } from "../workbench-panel";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

// ── helpers ──────────────────────────────────────────────────────────────────

function renderNav(beta: boolean) {
  featuresBeta = beta;
  return render(<WorkbenchNavBar threadId="t1" />);
}

// Localiza o botão pelo ícone SVG que está dentro dele (via data-testid do lucide).
// Como não temos data-testid nos botões, pegamos pelo índice da lista.
function getButtons(container: HTMLElement) {
  return Array.from(container.querySelectorAll("button"));
}

// ── Testes ───────────────────────────────────────────────────────────────────

describe("WorkbenchNavBar — BETA_TABS e ComingSoonTabButton", () => {
  describe("com enableFeaturesBeta = false (comportamento de produção)", () => {
    it("renderiza botão para context_graph que é clicável (não disabled)", () => {
      const { container } = renderNav(false);
      const btns = getButtons(container);
      // 3 tabs no mock: files (0), context_graph (1), terminal (2)
      expect(btns[1]).not.toBeDisabled();
    });

    it("clicar em context_graph despacha toast info com 'em breve'", () => {
      const { container } = renderNav(false);
      const btns = getButtons(container);
      fireEvent.click(btns[1]);
      expect(mockPush).toHaveBeenCalledOnce();
      expect(mockPush).toHaveBeenCalledWith(
        expect.objectContaining({ level: "info" }),
      );
    });

    it("clicar em context_graph NÃO chama selectTab", () => {
      const { container } = renderNav(false);
      fireEvent.click(getButtons(container)[1]);
      expect(mockSelectTab).not.toHaveBeenCalled();
    });

    it("clicar em tab normal (files) chama selectTab e NÃO despacha toast", () => {
      const { container } = renderNav(false);
      fireEvent.click(getButtons(container)[0]);
      expect(mockSelectTab).toHaveBeenCalledWith("t1", "files");
      expect(mockPush).not.toHaveBeenCalled();
    });
  });

  describe("com enableFeaturesBeta = true (comportamento de dev)", () => {
    it("clicar em context_graph chama selectTab (funcional em dev)", () => {
      const { container } = renderNav(true);
      fireEvent.click(getButtons(container)[1]);
      expect(mockSelectTab).toHaveBeenCalledWith("t1", "context_graph");
    });

    it("clicar em context_graph NÃO despacha toast (feature habilitada)", () => {
      const { container } = renderNav(true);
      fireEvent.click(getButtons(container)[1]);
      expect(mockPush).not.toHaveBeenCalled();
    });
  });

  describe("edge cases", () => {
    it("tab normal (terminal) chama selectTab independentemente da flag", () => {
      const { container } = renderNav(false);
      fireEvent.click(getButtons(container)[2]);
      expect(mockSelectTab).toHaveBeenCalledWith("t1", "terminal");
      expect(mockPush).not.toHaveBeenCalled();
    });

    it("toast despacha apenas uma vez por clique (sem duplicação)", () => {
      const { container } = renderNav(false);
      const btn = getButtons(container)[1];
      fireEvent.click(btn);
      fireEvent.click(btn);
      expect(mockPush).toHaveBeenCalledTimes(2);
    });
  });
});

describe("ComingSoonTabButton — em isolamento via WorkbenchNavBar", () => {
  beforeEach(() => {
    featuresBeta = false;
  });

  it("botão não tem atributo disabled (é clicável)", () => {
    const { container } = render(<WorkbenchNavBar threadId="t2" />);
    const btns = getButtons(container);
    expect(btns[1].hasAttribute("disabled")).toBe(false);
  });

  it("toast payload inclui description com o nome do tab", () => {
    const { container } = render(<WorkbenchNavBar threadId="t3" />);
    fireEvent.click(getButtons(container)[1]);
    expect(mockPush).toHaveBeenCalledWith(
      expect.objectContaining({
        level: "info",
        description: expect.any(String),
      }),
    );
  });
});

describe("WorkbenchNavBar — prop side (layout IDE vs Assistente)", () => {
  it('side="left" aplica border-r na raiz (IDE: workbench à esquerda do editor)', () => {
    const { container } = render(<WorkbenchNavBar threadId="t1" side="left" />);
    const root = container.firstChild as HTMLElement;
    expect(root.className).toContain("border-r");
    expect(root.className).not.toContain("border-l");
  });

  it('side="right" (padrão) aplica border-l na raiz (Assistente: workbench à direita)', () => {
    const { container } = render(
      <WorkbenchNavBar threadId="t1" side="right" />,
    );
    const root = container.firstChild as HTMLElement;
    expect(root.className).toContain("border-l");
    expect(root.className).not.toContain("border-r");
  });

  it("sem prop side usa border-l por padrão", () => {
    const { container } = render(<WorkbenchNavBar threadId="t1" />);
    const root = container.firstChild as HTMLElement;
    expect(root.className).toContain("border-l");
  });

  it('side="right" renderiza spacer h-16 (alinha com o Header no layout Assistente)', () => {
    const { container } = render(
      <WorkbenchNavBar threadId="t1" side="right" />,
    );
    expect(container.querySelector(".h-16")).not.toBeNull();
  });

  it('side="left" não renderiza spacer h-16 (Header já está no topo no layout IDE)', () => {
    const { container } = render(<WorkbenchNavBar threadId="t1" side="left" />);
    expect(container.querySelector(".h-16")).toBeNull();
  });
});

vi.mock("@/components/workbench/terminal/terminal-panel", () => ({
  TerminalPanel: () => null,
}));
vi.mock("@/components/workbench/files/files-tab", () => ({
  FilesTab: () => null,
}));
vi.mock("@/components/workbench/git/git-tab", () => ({
  GitTab: () => null,
}));
vi.mock("@/components/workbench/tabs/plan-tab", () => ({
  PlanTab: () => null,
}));
vi.mock("@/components/workbench/tabs/preview-tab", () => ({
  PreviewTab: () => null,
}));
vi.mock("@/components/workbench/tabs/memory-tab", () => ({
  MemoryTab: () => null,
}));
vi.mock("@/components/workbench/tabs/tasks-tab", () => ({
  TasksTab: () => null,
}));

describe("WorkbenchContent — prop side (layout IDE vs Assistente)", () => {
  it('side="left" aplica border-r na raiz', () => {
    const { container } = render(
      <WorkbenchContent threadId="t1" side="left" />,
    );
    const root = container.firstChild as HTMLElement;
    expect(root.className).toContain("border-r");
    expect(root.className).not.toContain("border-l");
  });

  it('side="right" (padrão) aplica border-l na raiz', () => {
    const { container } = render(
      <WorkbenchContent threadId="t1" side="right" />,
    );
    const root = container.firstChild as HTMLElement;
    expect(root.className).toContain("border-l");
    expect(root.className).not.toContain("border-r");
  });

  it("sem prop side usa border-l por padrão", () => {
    const { container } = render(<WorkbenchContent threadId="t1" />);
    const root = container.firstChild as HTMLElement;
    expect(root.className).toContain("border-l");
  });
});

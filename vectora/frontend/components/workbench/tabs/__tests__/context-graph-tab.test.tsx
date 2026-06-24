// @vitest-environment jsdom
/**
 * ContextGraphTab — renderização condicional por status + interações.
 *
 * Testa: not_built / running / error / done, botão Construir, perguntas
 * sugeridas clicáveis, god nodes clicáveis e crédito do graphify.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  render,
  screen,
  fireEvent,
  act,
  cleanup,
} from "@testing-library/react";

// ── mocks de dependências ────────────────────────────────────────────────────

vi.mock("@/lib/paraglide/messages", () => ({
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

vi.mock("@/lib/stores/workspaces-store", () => ({
  useWorkspacesStore: (sel: (s: { active_id: string }) => unknown) =>
    sel({ active_id: "ws1" }),
}));

const mockBuild = vi.fn();
const mockGetHtmlUrl = vi.fn(() => "/workspaces/ws1/context-graph/html");
const mockFetchStatus = vi.fn();
const mockUseContextGraph = vi.fn();

vi.mock("@/lib/hooks/use-context-graph", () => ({
  useContextGraph: (...args: unknown[]) => mockUseContextGraph(...args),
}));

// ── helpers ──────────────────────────────────────────────────────────────────

function setup(
  overrides: {
    status?: object;
    report?: string | null;
    loading?: boolean;
  } = {},
) {
  mockUseContextGraph.mockReturnValue({
    status: { status: "not_built" },
    report: null,
    loading: false,
    build: mockBuild,
    getHtmlUrl: mockGetHtmlUrl,
    fetchStatus: mockFetchStatus,
    ...overrides,
  });
}

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

// Importação após os mocks
import { ContextGraphTab } from "@/components/workbench/tabs/context-graph-tab";

// ── testes ───────────────────────────────────────────────────────────────────

describe("ContextGraphTab", () => {
  describe("estado not_built", () => {
    it("exibe mensagem graph_not_built", () => {
      setup();
      render(<ContextGraphTab threadId="t1" />);
      expect(screen.getByText("graph_not_built")).toBeTruthy();
    });

    it("botão mostra graph_build_button", () => {
      setup();
      render(<ContextGraphTab threadId="t1" />);
      expect(screen.getByText("graph_build_button")).toBeTruthy();
    });

    it("clicar no botão chama build()", async () => {
      setup();
      render(<ContextGraphTab threadId="t1" />);
      const btn = document.querySelector("button") as HTMLButtonElement;
      await act(async () => {
        fireEvent.click(btn);
      });
      expect(mockBuild).toHaveBeenCalledTimes(1);
    });

    it("botão está habilitado em not_built", () => {
      setup();
      render(<ContextGraphTab threadId="t1" />);
      const btn = document.querySelector("button") as HTMLButtonElement;
      expect(btn.disabled).toBe(false);
    });
  });

  describe("estado running", () => {
    it("exibe graph_building", () => {
      setup({ status: { status: "running" } });
      render(<ContextGraphTab threadId="t1" />);
      expect(screen.getAllByText("graph_building").length).toBeGreaterThan(0);
    });

    it("botão está desabilitado", () => {
      setup({ status: { status: "running" } });
      render(<ContextGraphTab threadId="t1" />);
      const btn = document.querySelector("button") as HTMLButtonElement;
      expect(btn.disabled).toBe(true);
    });

    it("botão está desabilitado quando loading=true", () => {
      setup({ loading: true });
      render(<ContextGraphTab threadId="t1" />);
      const btn = document.querySelector("button") as HTMLButtonElement;
      expect(btn.disabled).toBe(true);
    });
  });

  describe("estado error", () => {
    it("exibe a mensagem de erro", () => {
      setup({ status: { status: "error", error: "Pipeline falhou" } });
      render(<ContextGraphTab threadId="t1" />);
      expect(screen.getByText("Pipeline falhou")).toBeTruthy();
    });

    it("exibe mensagem genérica se error é null", () => {
      setup({ status: { status: "error", error: null } });
      render(<ContextGraphTab threadId="t1" />);
      expect(screen.getByText("Erro desconhecido")).toBeTruthy();
    });
  });

  describe("estado done", () => {
    it("exibe contagem de nós e arestas", () => {
      setup({ status: { status: "done", node_count: 42, edge_count: 17 } });
      render(<ContextGraphTab threadId="t1" />);
      expect(screen.getByText("42 nós")).toBeTruthy();
      expect(screen.getByText("17 arestas")).toBeTruthy();
    });

    it("botão muda para graph_rebuild_button", () => {
      setup({ status: { status: "done" } });
      render(<ContextGraphTab threadId="t1" />);
      expect(screen.getByText("graph_rebuild_button")).toBeTruthy();
    });

    it("exibe link para grafo interativo", () => {
      setup({ status: { status: "done" } });
      render(<ContextGraphTab threadId="t1" />);
      const link = document.querySelector("a[href]") as HTMLAnchorElement;
      expect(link).not.toBeNull();
      expect(link.href).toContain("context-graph/html");
    });
  });

  describe("perguntas sugeridas e god nodes", () => {
    const REPORT =
      "**God nodes** — top conectados\n- AuthService\n- TokenUtils\n\n**Perguntas sugeridas**\n- O que faz login?\n- Como Token é gerado?\n";

    it("perguntas clicáveis chamam onSendPrompt com texto da pergunta", async () => {
      const onSendPrompt = vi.fn();
      setup({ status: { status: "done" }, report: REPORT });
      render(<ContextGraphTab threadId="t1" onSendPrompt={onSendPrompt} />);
      const btn = screen.getByText("O que faz login?");
      await act(async () => {
        fireEvent.click(btn);
      });
      expect(onSendPrompt).toHaveBeenCalledWith("O que faz login?");
    });

    it("segunda pergunta também envia via onSendPrompt", async () => {
      const onSendPrompt = vi.fn();
      setup({ status: { status: "done" }, report: REPORT });
      render(<ContextGraphTab threadId="t1" onSendPrompt={onSendPrompt} />);
      const btn = screen.getByText("Como Token é gerado?");
      await act(async () => {
        fireEvent.click(btn);
      });
      expect(onSendPrompt).toHaveBeenCalledWith("Como Token é gerado?");
    });

    it("god nodes clicáveis enviam prompt de explain com o nome do nó", async () => {
      const onSendPrompt = vi.fn();
      setup({ status: { status: "done" }, report: REPORT });
      render(<ContextGraphTab threadId="t1" onSendPrompt={onSendPrompt} />);
      const btn = screen.getByText("AuthService");
      await act(async () => {
        fireEvent.click(btn);
      });
      expect(onSendPrompt).toHaveBeenCalledWith(
        expect.stringContaining("AuthService"),
      );
    });

    it("sem onSendPrompt clicar na pergunta não lança erro", async () => {
      setup({ status: { status: "done" }, report: REPORT });
      render(<ContextGraphTab threadId="t1" />);
      const btn = screen.getByText("O que faz login?");
      await expect(
        act(async () => {
          fireEvent.click(btn);
        }),
      ).resolves.not.toThrow();
    });
  });

  describe("crédito e report toggle", () => {
    it("exibe crédito do graphify no rodapé", () => {
      setup();
      render(<ContextGraphTab threadId="t1" />);
      expect(screen.getByText("graph_credit")).toBeTruthy();
    });

    it("toggle do report expande e colapsa o markdown", async () => {
      const REPORT_MD =
        "**God nodes**\n- X\n\n**Perguntas sugeridas**\n- Algo?\n";
      setup({ status: { status: "done" }, report: REPORT_MD });
      render(<ContextGraphTab threadId="t1" />);

      const toggleBtn = screen.getByText("graph_report_title");
      await act(async () => {
        fireEvent.click(toggleBtn);
      });
      const pre = document.querySelector("pre");
      expect(pre).not.toBeNull();
      expect(pre!.textContent).toContain("God nodes");

      await act(async () => {
        fireEvent.click(screen.getByText("Ocultar"));
      });
      expect(document.querySelector("pre")).toBeNull();
    });
  });
});

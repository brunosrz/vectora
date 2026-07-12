// @vitest-environment jsdom
/**
 * RAG é escopo de workspace (LanceDB persiste entre sessões), não de thread
 * — uma sessão nova (sem ragCitations ainda) num workspace já indexado não
 * pode mostrar o mesmo "vazio" genérico de um workspace de verdade vazio.
 * A aba consulta GET /rag/workspace-summary pra distinguir os dois casos.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  render,
  screen,
  waitFor,
  cleanup,
  fireEvent,
} from "@testing-library/react";
import { MemoryTab } from "../memory-tab";

vi.mock("@/lib/paraglide/messages", () => ({
  m: new Proxy(
    {},
    {
      get:
        (_t, prop) =>
        (...args: unknown[]) => {
          const params = args[0] as Record<string, unknown> | undefined;
          return params
            ? `${String(prop)}(${JSON.stringify(params)})`
            : String(prop);
        },
    },
  ),
}));

const mockMessages = vi.fn();
vi.mock("@/lib/hooks/chat/use-thread-messages", () => ({
  useThreadMessages: (threadId: string) => [mockMessages(threadId), vi.fn()],
}));

vi.mock("@/lib/stores/workspaces-store", () => ({
  useWorkspacesStore: (
    sel: (s: { getActive: () => { id: string } | undefined }) => unknown,
  ) => sel({ getActive: () => ({ id: "ws-1" }) }),
}));

vi.mock("@/lib/stores/rag-jobs-store", () => ({
  useRagJobsStore: (sel: (s: { jobs: Record<string, never> }) => unknown) =>
    sel({ jobs: {} }),
}));

vi.mock("@/components/workbench/rag-settings-panel", () => ({
  useRagSettings: () => ({
    open: false,
    toggle: vi.fn(),
    close: vi.fn(),
    settings: {},
    collections: [],
    patch: vi.fn(),
    loadCollections: vi.fn(),
    deleteCollection: vi.fn(),
  }),
  RagSettingsButton: () => <div data-testid="rag-settings-btn-stub" />,
  RagSettingsSlidePanel: () => <div data-testid="rag-settings-panel-stub" />,
}));

beforeEach(() => {
  mockMessages.mockReturnValue([]);
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("MemoryTab", () => {
  it("mostra 'memória vazia' genérico quando o workspace nunca foi indexado (edge)", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(JSON.stringify({ collections: [] }))),
    );

    render(<MemoryTab threadId="t1" />);

    await waitFor(() =>
      expect(
        screen.getByText("workbench_memory_empty_title"),
      ).toBeInTheDocument(),
    );
  });

  it("mostra que já há conteúdo indexado quando o workspace tem RAG de sessão anterior (regressão do bug)", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => {
        if (String(url).includes("/rag/workspace-summary")) {
          return new Response(
            JSON.stringify({
              collections: [
                { name: "articles", count: 3 },
                { name: "web_cache", count: 2 },
              ],
            }),
          );
        }
        throw new Error(`unmocked fetch: ${url}`);
      }),
    );

    render(<MemoryTab threadId="t1" />);

    await waitFor(() =>
      expect(
        screen.getByText("workbench_memory_indexed_title"),
      ).toBeInTheDocument(),
    );
    expect(
      screen.getByText('workbench_memory_indexed_desc({"n":5})'),
    ).toBeInTheDocument();
    // Não deve mostrar o "vazio" genérico junto.
    expect(
      screen.queryByText("workbench_memory_empty_title"),
    ).not.toBeInTheDocument();
  });

  it("chama /rag/workspace-summary com o workspace_id ativo", async () => {
    const fetchMock = vi.fn(
      async () => new Response(JSON.stringify({ collections: [] })),
    );
    vi.stubGlobal("fetch", fetchMock);

    render(<MemoryTab threadId="t1" />);

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        "/rag/workspace-summary?workspace_id=ws-1",
      ),
    );
  });

  it("tolera falha de rede no resumo do workspace e cai no vazio genérico (edge)", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new Error("network down");
      }),
    );

    render(<MemoryTab threadId="t1" />);

    await waitFor(() =>
      expect(
        screen.getByText("workbench_memory_empty_title"),
      ).toBeInTheDocument(),
    );
  });

  it("prioriza atividade/citações da thread atual sobre o resumo do workspace quando ambos existem", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(
        async () =>
          new Response(
            JSON.stringify({ collections: [{ name: "articles", count: 3 }] }),
          ),
      ),
    );
    mockMessages.mockReturnValue([
      {
        id: "m1",
        role: "assistant",
        content: "resposta",
        ragCitations: [
          { source: "doc.md", chunk: "trecho recuperado", index: 1 },
        ],
      },
    ]);

    render(<MemoryTab threadId="t1" />);

    await waitFor(() => expect(screen.getByText("doc.md")).toBeInTheDocument());
    expect(
      screen.queryByText("workbench_memory_indexed_title"),
    ).not.toBeInTheDocument();
  });

  it("busca /rag/search com o texto digitado e mostra os resultados", async () => {
    const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
      if (String(url).includes("/rag/workspace-summary")) {
        return new Response(JSON.stringify({ collections: [] }));
      }
      if (String(url) === "/rag/search") {
        const body = JSON.parse(String(init?.body));
        expect(body).toEqual({ query: "auth", workspace_id: "ws-1" });
        return new Response(
          JSON.stringify({
            results: [{ content: "trecho sobre auth", collection: "articles" }],
          }),
        );
      }
      throw new Error(`unmocked fetch: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<MemoryTab threadId="t1" />);

    fireEvent.change(
      screen.getByPlaceholderText("workbench_memory_search_placeholder"),
      { target: { value: "auth" } },
    );

    await waitFor(
      () => expect(screen.getAllByText("articles").length).toBeGreaterThan(0),
      { timeout: 2000 },
    );
    fireEvent.click(screen.getByRole("button"));
    expect(screen.getByText("trecho sobre auth")).toBeInTheDocument();
  });

  it("mostra 'nenhum resultado' quando a busca não encontra nada (edge)", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => {
        if (String(url).includes("/rag/workspace-summary")) {
          return new Response(JSON.stringify({ collections: [] }));
        }
        if (String(url) === "/rag/search") {
          return new Response(JSON.stringify({ results: [] }));
        }
        throw new Error(`unmocked fetch: ${url}`);
      }),
    );

    render(<MemoryTab threadId="t1" />);

    fireEvent.change(
      screen.getByPlaceholderText("workbench_memory_search_placeholder"),
      { target: { value: "nada-aqui" } },
    );

    await waitFor(
      () =>
        expect(
          screen.getByText("workbench_memory_search_no_results"),
        ).toBeInTheDocument(),
      { timeout: 2000 },
    );
  });
});

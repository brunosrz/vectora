// @vitest-environment jsdom
/**
 * RotinasTab — testes de renderização e interações.
 * MemoriaTab — testes de carregamento, CRUD e erro.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  render,
  screen,
  cleanup,
  fireEvent,
  act,
  waitFor,
} from "@testing-library/react";

// ── fetch mock ───────────────────────────────────────────────────────────────

const ROUTINES: object[] = [];
const MEMORIES: {
  key: string;
  content: string;
  metadata: object;
  updated_at: string;
}[] = [];

const FETCH_MOCK = vi.fn(async (url: string, opts?: RequestInit) => {
  const method = opts?.method ?? "GET";
  const urlStr = String(url);

  // /memory routes — verificados antes dos genéricos POST/DELETE
  if (method === "GET" && urlStr.match(/\/memory(\?|$)/)) {
    return new Response(
      JSON.stringify({ memories: [...MEMORIES], total: MEMORIES.length }),
      { status: 200, headers: { "Content-Type": "application/json" } },
    );
  }
  if (method === "POST" && urlStr.match(/\/memory(\?|$)/)) {
    const body = JSON.parse(String(opts?.body ?? "{}"));
    const item = {
      key: body.key || `mem_${Date.now()}`,
      content: body.content,
      metadata: {},
      updated_at: new Date().toISOString(),
    };
    MEMORIES.push(item);
    return new Response(JSON.stringify({ status: "created", key: item.key }), {
      status: 201,
      headers: { "Content-Type": "application/json" },
    });
  }
  if (method === "PUT" && urlStr.match(/\/memory\/[^/]+$/)) {
    return new Response(JSON.stringify({ status: "updated" }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  }
  if (method === "DELETE" && urlStr.match(/\/memory\/[^/?]+$/)) {
    const key = urlStr.split("/memory/")[1];
    const idx = MEMORIES.findIndex((m) => m.key === key);
    if (idx >= 0) MEMORIES.splice(idx, 1);
    return new Response(JSON.stringify({ status: "deleted" }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  }
  if (method === "DELETE" && urlStr.match(/\/memory(\?|$)/)) {
    MEMORIES.length = 0;
    return new Response(JSON.stringify({ status: "deleted", deleted: 0 }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  }

  // /routines routes
  if (method === "GET" && urlStr.includes("/routines")) {
    return new Response(JSON.stringify(ROUTINES), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  }
  if (method === "POST") {
    const body = JSON.parse(String(opts?.body ?? "{}"));
    return new Response(
      JSON.stringify({
        id: "new-1",
        name: body.name,
        instruction: body.instruction,
        cron_expr: body.cron_expr,
        enabled: true,
        last_run_at: null,
        next_run_at: "2024-06-21T09:00:00",
      }),
      { status: 201, headers: { "Content-Type": "application/json" } },
    );
  }
  if (method === "DELETE") {
    return new Response(null, { status: 204 });
  }
  return new Response(JSON.stringify({}), { status: 200 });
});

beforeEach(() => {
  vi.stubGlobal("fetch", FETCH_MOCK);
  ROUTINES.length = 0;
  MEMORIES.length = 0;
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

// ── mocks ────────────────────────────────────────────────────────────────────

vi.mock("@/lib/stores/toast-store", () => ({
  useToastStore: { getState: () => ({ success: vi.fn(), error: vi.fn() }) },
}));

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

vi.mock("@/lib/i18n-dyn", () => ({
  mDyn: (_key: string, params: { n: number }) => `${params.n} memória(s)`,
}));

// ── RotinasTab ────────────────────────────────────────────────────────────────

async function renderRotinasTab() {
  const { RotinasTab } = await import("../rotinas-tab");
  return render(<RotinasTab />);
}

describe("RotinasTab (Sprint 8)", () => {
  it("exibe mensagem de lista vazia quando não há rotinas", async () => {
    await act(async () => {
      await renderRotinasTab();
    });
    expect(document.querySelector("[data-testid='routine-item']")).toBeNull();
  });

  it("botão 'Nova rotina' abre o dialog de criação", async () => {
    await act(async () => {
      await renderRotinasTab();
    });
    const btn = document.querySelector(
      "[data-testid='routines-new-btn']",
    ) as HTMLElement;
    expect(btn).not.toBeNull();
    await act(async () => {
      fireEvent.click(btn);
    });
    expect(
      document.querySelector("[data-testid='routine-name-input']"),
    ).not.toBeNull();
  });

  it("salvar rotina chama POST /routines e exibe novo item", async () => {
    await act(async () => {
      await renderRotinasTab();
    });
    const newBtn = document.querySelector(
      "[data-testid='routines-new-btn']",
    ) as HTMLElement;
    await act(async () => {
      fireEvent.click(newBtn);
    });
    const nameInput = document.querySelector(
      "[data-testid='routine-name-input']",
    ) as HTMLInputElement;
    const instrInput = document.querySelector(
      "[data-testid='routine-instruction-input']",
    ) as HTMLTextAreaElement;
    await act(async () => {
      fireEvent.change(nameInput, { target: { value: "Minha rotina" } });
      fireEvent.change(instrInput, { target: { value: "faça X" } });
    });
    const saveBtn = document.querySelector(
      "[data-testid='routine-save-btn']",
    ) as HTMLElement;
    await act(async () => {
      fireEvent.click(saveBtn);
    });
    expect(
      document.querySelector("[data-testid='routine-item']"),
    ).not.toBeNull();
  });
});

// ── MemoriaTab ────────────────────────────────────────────────────────────────

async function renderMemoriaTab() {
  const { MemoriaTab } = await import("../memoria-tab");
  return render(<MemoriaTab />);
}

describe("MemoriaTab", () => {
  it("exibe empty state quando não há memórias", async () => {
    await act(async () => {
      await renderMemoriaTab();
    });
    await waitFor(() => {
      // m proxy devolve o nome da prop como string
      expect(screen.queryByText("memory_empty_title")).toBeTruthy();
    });
  });

  it("lista memórias carregadas do servidor", async () => {
    MEMORIES.push({
      key: "idioma",
      content: "Prefere português",
      metadata: {},
      updated_at: "2024-01-01T00:00:00Z",
    });
    await act(async () => {
      await renderMemoriaTab();
    });
    await waitFor(() => {
      expect(screen.getByText("idioma")).toBeTruthy();
      expect(screen.getByText("Prefere português")).toBeTruthy();
    });
  });

  it("exibe mensagem de erro quando o servidor retorna 500", async () => {
    FETCH_MOCK.mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: "erro" }), { status: 500 }),
    );
    await act(async () => {
      await renderMemoriaTab();
    });
    await waitFor(() => {
      expect(screen.getByText("memory_error_load")).toBeTruthy();
    });
  });

  it("cria nova memória: POST /memory chamado com conteúdo correto", async () => {
    await act(async () => {
      await renderMemoriaTab();
    });
    await waitFor(() => screen.getByText("memory_add"));

    await act(async () => {
      fireEvent.click(screen.getByText("memory_add"));
    });

    await waitFor(() => screen.getByText("memory_add_title"));

    const textarea = screen.getByPlaceholderText(
      "memory_add_content_placeholder",
    );
    await act(async () => {
      fireEvent.change(textarea, {
        target: { value: "nova memória de teste" },
      });
    });

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "memory_save" }));
    });

    await waitFor(() => {
      const calls = FETCH_MOCK.mock.calls;
      const postCall = calls.find(([, o]) => o?.method === "POST");
      expect(postCall).toBeTruthy();
      const body = JSON.parse(String(postCall![1]!.body));
      expect(body.content).toBe("nova memória de teste");
    });
  });

  it("deleta memória: DELETE /memory/:key chamado", async () => {
    MEMORIES.push({
      key: "del_test",
      content: "Conteúdo a deletar",
      metadata: {},
      updated_at: "2024-01-01T00:00:00Z",
    });
    await act(async () => {
      await renderMemoriaTab();
    });
    await waitFor(() => screen.getByText("Conteúdo a deletar"));

    const deleteButtons = screen.getAllByText("memory_delete");
    await act(async () => {
      fireEvent.click(deleteButtons[0]);
    });

    await waitFor(() => {
      const calls = FETCH_MOCK.mock.calls;
      const deleteCall = calls.find(
        ([url, o]) =>
          o?.method === "DELETE" && String(url).includes("del_test"),
      );
      expect(deleteCall).toBeTruthy();
    });
  });
});

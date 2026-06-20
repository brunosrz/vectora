// @vitest-environment jsdom
/**
 * MemoriaTab — testes de renderização, carregamento e interações CRUD.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  render,
  screen,
  cleanup,
  fireEvent,
  waitFor,
  act,
} from "@testing-library/react";

// ── i18n mock ────────────────────────────────────────────────────────────────

vi.mock("@/lib/paraglide/messages", () => ({
  m: {
    memory_error_load: () => "Erro ao carregar memórias",
    memory_error_save: () => "Erro ao salvar",
    memory_error_delete: () => "Erro ao deletar",
    memory_error_create: () => "Erro ao criar memória",
    memory_error_clear: () => "Erro ao limpar",
    memory_empty_title: () => "Nenhuma memória",
    memory_subtitle: () => "Memórias salvas pelo agente",
    memory_add: () => "Adicionar",
    memory_clear_all: () => "Limpar tudo",
    memory_empty_hint: () => "Sem memórias ainda",
    memory_empty_hint2: () => "O agente salva memórias automaticamente",
    memory_save: () => "Salvar",
    memory_cancel: () => "Cancelar",
    memory_edit: () => "Editar",
    memory_delete: () => "Deletar",
    memory_add_title: () => "Adicionar memória",
    memory_add_desc: () => "Adicione uma nova memória manualmente",
    memory_add_content_label: () => "Conteúdo",
    memory_add_content_placeholder: () => "Digite o conteúdo",
    memory_add_key_label: () => "Identificador (opcional)",
    memory_add_key_placeholder: () => "ex: preferencia_idioma",
    memory_clear_title: () => "Limpar memórias",
    memory_clear_desc: () => "Isso remove todas as memórias permanentemente",
  },
}));

vi.mock("@/lib/i18n-dyn", () => ({
  mDyn: (_key: string, params: { n: number }) => `${params.n} memória(s)`,
}));

// ── fetch mock ───────────────────────────────────────────────────────────────

const MEMORIES: object[] = [];

const FETCH_MOCK = vi.fn(async (url: string, opts?: RequestInit) => {
  const method = opts?.method ?? "GET";
  const urlStr = String(url);

  // GET /memory
  if (method === "GET" && urlStr.match(/\/memory(\?|$)/)) {
    return new Response(
      JSON.stringify({ memories: [...MEMORIES], total: MEMORIES.length }),
      { status: 200, headers: { "Content-Type": "application/json" } },
    );
  }

  // POST /memory — criar
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

  // PUT /memory/:key
  if (method === "PUT" && urlStr.match(/\/memory\/[^/]+$/)) {
    return new Response(JSON.stringify({ status: "updated", key: "any" }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  }

  // DELETE /memory/:key
  if (method === "DELETE" && urlStr.match(/\/memory\/[^/?]+$/)) {
    return new Response(JSON.stringify({ status: "deleted", key: "any" }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  }

  // DELETE /memory — limpar tudo
  if (method === "DELETE" && urlStr.match(/\/memory(\?|$)/)) {
    const count = MEMORIES.length;
    MEMORIES.length = 0;
    return new Response(JSON.stringify({ status: "deleted", deleted: count }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  }

  return new Response(JSON.stringify({}), { status: 200 });
});

beforeEach(() => {
  vi.stubGlobal("fetch", FETCH_MOCK);
  MEMORIES.length = 0;
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

// ── Subject ───────────────────────────────────────────────────────────────────
import { MemoriaTab } from "../memoria-tab";

// ── Testes ────────────────────────────────────────────────────────────────────

describe("MemoriaTab", () => {
  it("exibe empty state quando não há memórias", async () => {
    render(<MemoriaTab />);
    await waitFor(() => {
      expect(screen.queryByText(/Nenhuma memória/i)).toBeTruthy();
    });
  });

  it("lista memórias carregadas do servidor", async () => {
    MEMORIES.push({
      key: "idioma",
      content: "Prefere português",
      metadata: {},
      updated_at: "2024-01-01T00:00:00Z",
    });
    render(<MemoriaTab />);
    await waitFor(() => {
      expect(screen.getByText("idioma")).toBeTruthy();
      expect(screen.getByText("Prefere português")).toBeTruthy();
    });
  });

  it("exibe mensagem de erro quando o servidor retorna 500", async () => {
    FETCH_MOCK.mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: "Internal error" }), {
        status: 500,
      }),
    );
    render(<MemoriaTab />);
    await waitFor(() => {
      expect(screen.getByText("Erro ao carregar memórias")).toBeTruthy();
    });
  });

  it("cria nova memória e atualiza a lista", async () => {
    render(<MemoriaTab />);
    await waitFor(() => screen.getByText("Adicionar"));

    fireEvent.click(screen.getByText("Adicionar"));

    await waitFor(() => screen.getByText("Adicionar memória"));

    const textarea = screen.getByPlaceholderText("Digite o conteúdo");
    fireEvent.change(textarea, { target: { value: "Nova memória de teste" } });

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Salvar" }));
    });

    await waitFor(() => {
      const calls = FETCH_MOCK.mock.calls;
      const postCall = calls.find(([, opts]) => opts?.method === "POST");
      expect(postCall).toBeTruthy();
      const body = JSON.parse(String(postCall![1]!.body));
      expect(body.content).toBe("Nova memória de teste");
    });
  });

  it("deleta memória da lista", async () => {
    MEMORIES.push({
      key: "del_test",
      content: "Conteúdo a deletar",
      metadata: {},
      updated_at: "2024-01-01T00:00:00Z",
    });
    render(<MemoriaTab />);
    await waitFor(() => screen.getByText("Conteúdo a deletar"));

    const deleteButtons = screen.getAllByText("Deletar");
    await act(async () => {
      fireEvent.click(deleteButtons[0]);
    });

    await waitFor(() => {
      const calls = FETCH_MOCK.mock.calls;
      const deleteCall = calls.find(
        ([url, opts]) =>
          opts?.method === "DELETE" && String(url).includes("del_test"),
      );
      expect(deleteCall).toBeTruthy();
    });
  });

  it("limpa todas as memórias com confirmação", async () => {
    MEMORIES.push(
      { key: "k1", content: "c1", metadata: {}, updated_at: "" },
      { key: "k2", content: "c2", metadata: {}, updated_at: "" },
    );
    render(<MemoriaTab />);
    await waitFor(() => screen.getByText("Limpar tudo"));

    fireEvent.click(screen.getByText("Limpar tudo"));
    await waitFor(() => screen.getByText("Limpar memórias"));

    await act(async () => {
      const confirmBtns = screen.getAllByText("Limpar tudo");
      fireEvent.click(confirmBtns[confirmBtns.length - 1]);
    });

    await waitFor(() => {
      const calls = FETCH_MOCK.mock.calls;
      const clearCall = calls.find(
        ([url, opts]) =>
          opts?.method === "DELETE" && String(url).match(/\/memory(\?|$)/),
      );
      expect(clearCall).toBeTruthy();
    });
  });
});

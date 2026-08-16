// @vitest-environment jsdom
/**
 * Painel de detalhe do card do Kanban — comentários + timeline de
 * transições, aberto pelo botão "Ver detalhes" no `TaskCard`.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
} from "@testing-library/react";

import { overwriteGetLocale, baseLocale } from "@/lib/paraglide/runtime";
import { KanbanBoard } from "../kanban-board";

function task(over: Record<string, unknown> = {}) {
  return {
    id: "t1",
    name: "tarefa",
    status: "todo",
    block_kind: null,
    block_reason: null,
    ...over,
  };
}

class MockEventSource {
  static instances: MockEventSource[] = [];
  closed = false;
  constructor(public url: string) {
    MockEventSource.instances.push(this);
  }
  addEventListener() {}
  close() {
    this.closed = true;
  }
}

beforeEach(() => {
  overwriteGetLocale(() => "pt");
  vi.stubGlobal("EventSource", MockEventSource);
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  overwriteGetLocale(() => baseLocale);
});

async function abrirDetalhes() {
  const botao = screen.getByRole("button", { name: /ver detalhes/i });
  await act(async () => {
    botao.click();
  });
}

describe("TaskDetailPanel", () => {
  it("abre o painel, busca comentários/eventos sob demanda e lista o resultado", async () => {
    const chamadas: string[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => {
        chamadas.push(url);
        if (url.endsWith("/comments")) {
          return new Response(
            JSON.stringify([
              {
                id: "c1",
                user_id: "u1",
                body: "primeiro comentário",
                created_at: "2026-01-01T00:00:00Z",
              },
            ]),
            { status: 200 },
          );
        }
        if (url.endsWith("/events")) {
          return new Response(
            JSON.stringify([
              {
                id: "e1",
                from_status: "todo",
                to_status: "ready",
                block_kind: null,
                block_reason: null,
                created_at: "2026-01-01T00:00:00Z",
              },
            ]),
            { status: 200 },
          );
        }
        return new Response(JSON.stringify([task()]), { status: 200 });
      }),
    );

    render(<KanbanBoard threadId="s1" />);
    await act(async () => {});
    await abrirDetalhes();

    expect(chamadas.some((c) => c.endsWith("/tasks/t1/comments"))).toBe(true);
    expect(chamadas.some((c) => c.endsWith("/tasks/t1/events"))).toBe(true);
    expect(screen.getByText("primeiro comentário")).toBeInTheDocument();
    expect(screen.getByText(/todo → ready/i)).toBeInTheDocument();
  });

  it("enviar comentário faz POST e recarrega a lista", async () => {
    const chamadas: { url: string; method: string; body?: string }[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, init?: RequestInit) => {
        chamadas.push({
          url,
          method: init?.method ?? "GET",
          body: init?.body as string | undefined,
        });
        if (url.endsWith("/comments") && init?.method === "POST") {
          return new Response(
            JSON.stringify({
              id: "c1",
              user_id: "u1",
              body: "novo comentário",
              created_at: "2026-01-01T00:00:00Z",
            }),
            { status: 201 },
          );
        }
        if (url.endsWith("/comments"))
          return new Response("[]", { status: 200 });
        if (url.endsWith("/events")) return new Response("[]", { status: 200 });
        return new Response(JSON.stringify([task()]), { status: 200 });
      }),
    );

    render(<KanbanBoard threadId="s1" />);
    await act(async () => {});
    await abrirDetalhes();

    const textarea = screen.getByLabelText(/escreva um comentário/i);
    await act(async () => {
      fireEvent.change(textarea, { target: { value: "novo comentário" } });
    });
    await act(async () => {
      screen.getByRole("button", { name: /^comentar$/i }).click();
    });

    const post = chamadas.find(
      (c) => c.method === "POST" && c.url.endsWith("/comments"),
    );
    expect(post).toBeTruthy();
    expect(JSON.parse(post?.body ?? "{}")).toEqual({ body: "novo comentário" });
  });

  it("falha de rede ao comentar mostra erro discreto, sem quebrar o painel", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, init?: RequestInit) => {
        if (url.endsWith("/comments") && init?.method === "POST") {
          return new Response("erro", { status: 500 });
        }
        if (url.endsWith("/comments"))
          return new Response("[]", { status: 200 });
        if (url.endsWith("/events")) return new Response("[]", { status: 200 });
        return new Response(JSON.stringify([task()]), { status: 200 });
      }),
    );

    render(<KanbanBoard threadId="s1" />);
    await act(async () => {});
    await abrirDetalhes();

    const textarea = screen.getByLabelText(/escreva um comentário/i);
    await act(async () => {
      fireEvent.change(textarea, { target: { value: "vai falhar" } });
    });
    await act(async () => {
      screen.getByRole("button", { name: /^comentar$/i }).click();
    });

    expect(
      await screen.findByText(/não foi possível enviar o comentário/i),
    ).toBeInTheDocument();
    // O painel segue funcional — o título do card continua visível.
    expect(screen.getAllByText("tarefa").length).toBeGreaterThan(0);
  });

  it("painel vazio mostra as mensagens de 'nenhum comentário'/'nenhuma mudança'", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => {
        if (url.endsWith("/comments"))
          return new Response("[]", { status: 200 });
        if (url.endsWith("/events")) return new Response("[]", { status: 200 });
        return new Response(JSON.stringify([task()]), { status: 200 });
      }),
    );

    render(<KanbanBoard threadId="s1" />);
    await act(async () => {});
    await abrirDetalhes();

    expect(
      await screen.findByText(/nenhum comentário ainda/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/nenhuma mudança de status ainda/i),
    ).toBeInTheDocument();
  });
});

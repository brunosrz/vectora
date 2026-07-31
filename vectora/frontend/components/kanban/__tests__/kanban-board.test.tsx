// @vitest-environment jsdom
/**
 * Board do 3º modo de interface.
 *
 * Cinco colunas fixas; `triage`/`archived` existem no modelo mas ficam fora
 * — sete colunas viram ruído e essas duas não são o fluxo do dia a dia.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, render, screen, within } from "@testing-library/react";

import { overwriteGetLocale, baseLocale } from "@/lib/paraglide/runtime";
import { KanbanBoard } from "../kanban-board";

function mockTasks(tasks: unknown[]) {
  // A resposta real de GET /sessions/{id}/background/tasks é `list[TaskOut]`
  // — um array puro, não um envelope `{tasks: [...]}`.
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => new Response(JSON.stringify(tasks), { status: 200 })),
  );
}

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

beforeEach(() => overwriteGetLocale(() => "pt"));
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  overwriteGetLocale(() => baseLocale);
});

async function montar() {
  render(<KanbanBoard threadId="s1" />);
  await act(async () => {});
}

describe("KanbanBoard", () => {
  it("põe cada card na coluna do seu status", async () => {
    mockTasks([
      task({ id: "a", name: "na fila", status: "todo" }),
      task({ id: "b", name: "rodando", status: "running" }),
      task({ id: "c", name: "concluída", status: "done" }),
    ]);

    await montar();

    expect(
      within(screen.getByTestId("kanban-col-todo")).getByText("na fila"),
    ).toBeInTheDocument();
    expect(
      within(screen.getByTestId("kanban-col-running")).getByText("rodando"),
    ).toBeInTheDocument();
    expect(
      within(screen.getByTestId("kanban-col-done")).getByText("concluída"),
    ).toBeInTheDocument();
  });

  it("card bloqueado mostra o motivo", async () => {
    mockTasks([
      task({
        status: "blocked",
        block_kind: "needs_input",
        block_reason: "falta a chave da API",
      }),
    ]);

    await montar();

    expect(screen.getByText("falta a chave da API")).toBeInTheDocument();
  });

  it("dependência aparece como badge, não como coluna", async () => {
    mockTasks([task({ status: "todo", blocked_by: ["t0"] })]);

    await montar();

    expect(screen.getByText(/bloqueado por: t0/i)).toBeInTheDocument();
  });

  it("triage e archived não aparecem nas cinco colunas", async () => {
    // Erro/borda: mostrá-los junto encheria o board de cards fora do fluxo
    // ativo — os dois existem no modelo mas não têm coluna aqui.
    mockTasks([
      task({ id: "a", name: "em triagem", status: "triage" }),
      task({ id: "b", name: "arquivada", status: "archived" }),
    ]);

    await montar();

    expect(screen.queryByText("em triagem")).not.toBeInTheDocument();
    expect(screen.queryByText("arquivada")).not.toBeInTheDocument();
    expect(screen.getByText(/nenhuma tarefa/i)).toBeInTheDocument();
  });

  it("botão Desbloquear só aparece em cards blocked e chama /unblock", async () => {
    const chamadas: string[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, init?: RequestInit) => {
        chamadas.push(`${init?.method ?? "GET"} ${url}`);
        return new Response(
          JSON.stringify(
            init?.method === "POST"
              ? []
              : [task({ id: "a", status: "blocked", block_reason: "x" })],
          ),
          { status: 200 },
        );
      }),
    );

    await montar();
    const botao = screen.getByRole("button", { name: /desbloquear/i });
    await act(async () => {
      botao.click();
    });

    expect(
      chamadas.some((c) => c.startsWith("POST") && c.includes("/unblock")),
    ).toBe(true);
  });

  it("botão Cancelar não aparece em cards done, mas aparece nos demais", async () => {
    mockTasks([
      task({ id: "a", status: "todo" }),
      task({ id: "b", status: "done" }),
    ]);

    await montar();

    const colunaTodo = screen.getByTestId("kanban-col-todo");
    const colunaDone = screen.getByTestId("kanban-col-done");
    expect(
      within(colunaTodo).getByRole("button", { name: /cancelar/i }),
    ).toBeInTheDocument();
    expect(
      within(colunaDone).queryByRole("button", { name: /cancelar/i }),
    ).not.toBeInTheDocument();
  });

  it("falha ao carregar mostra board vazio, não tela de erro", async () => {
    // Erro/borda: as tarefas seguem rodando — só a visualização não carregou.
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new Error("rede fora");
      }),
    );

    await montar();

    expect(screen.getByText(/nenhuma tarefa/i)).toBeInTheDocument();
  });
});

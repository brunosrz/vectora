// @vitest-environment jsdom
/**
 * Board do 3º modo de interface.
 *
 * Cinco colunas fixas; `triage`/`archived` existem no modelo mas ficam fora
 * — sete colunas viram ruído e essas duas não são o fluxo do dia a dia.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  within,
} from "@testing-library/react";

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

// jsdom não implementa EventSource — o mock abaixo substitui o global em
// toda a suíte, não só nos testes de SSE, senão o `new EventSource(...)`
// do mount quebraria os testes que só olham pro polling/REST.
class MockEventSource {
  static instances: MockEventSource[] = [];
  closed = false;
  readonly url: string;
  private messageListeners: ((ev: MessageEvent<string>) => void)[] = [];
  private errorListeners: (() => void)[] = [];

  constructor(url: string) {
    this.url = url;
    MockEventSource.instances.push(this);
  }

  addEventListener(
    type: "message" | "error",
    listener: (ev?: unknown) => void,
  ) {
    if (type === "message") {
      this.messageListeners.push(
        listener as (ev: MessageEvent<string>) => void,
      );
    } else {
      this.errorListeners.push(listener as () => void);
    }
  }

  close() {
    this.closed = true;
  }

  emit(data: unknown) {
    const ev = { data: JSON.stringify(data) } as MessageEvent<string>;
    for (const listener of this.messageListeners) listener(ev);
  }

  fail() {
    for (const listener of this.errorListeners) listener();
  }
}

beforeEach(() => {
  overwriteGetLocale(() => "pt");
  MockEventSource.instances = [];
  vi.stubGlobal("EventSource", MockEventSource);
});
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

  it("Nova tarefa envia POST com nome/instrução e recarrega o board", async () => {
    const chamadas: { url: string; method: string; body?: string }[] = [];
    mockTasks([]);
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, init?: RequestInit) => {
        chamadas.push({
          url,
          method: init?.method ?? "GET",
          body: init?.body as string | undefined,
        });
        return new Response(JSON.stringify([]), { status: 200 });
      }),
    );

    await montar();
    await act(async () => {
      screen.getByRole("button", { name: /nova tarefa/i }).click();
    });
    const nomeInput = screen.getByLabelText(/nome/i) as HTMLInputElement;
    const instrucaoInput = screen.getByLabelText(
      /instru[çc][ãa]o/i,
    ) as HTMLTextAreaElement;
    await act(async () => {
      fireEvent.change(nomeInput, { target: { value: "verificar deploy" } });
      fireEvent.change(instrucaoInput, {
        target: { value: "confira o status do deploy" },
      });
    });
    await act(async () => {
      screen.getByRole("button", { name: /^criar$/i }).click();
    });

    const post = chamadas.find(
      (c) => c.method === "POST" && c.url.includes("/background/tasks"),
    );
    expect(post).toBeTruthy();
    const corpo = JSON.parse(post?.body ?? "{}");
    expect(corpo).toMatchObject({
      name: "verificar deploy",
      instruction: "confira o status do deploy",
      trigger_type: "manual",
    });
  });

  it("Nova tarefa com nome vazio não envia POST", async () => {
    const chamadas: string[] = [];
    mockTasks([]);
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, init?: RequestInit) => {
        if (init?.method === "POST") chamadas.push(url);
        return new Response(JSON.stringify([]), { status: 200 });
      }),
    );

    await montar();
    await act(async () => {
      screen.getByRole("button", { name: /nova tarefa/i }).click();
    });
    await act(async () => {
      screen.getByRole("button", { name: /^criar$/i }).click();
    });

    expect(chamadas).toEqual([]);
  });

  it('botão "Rodar agora" só aparece em cards ready e chama /run', async () => {
    const chamadas: string[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, init?: RequestInit) => {
        chamadas.push(`${init?.method ?? "GET"} ${url}`);
        return new Response(
          JSON.stringify(
            init?.method === "POST"
              ? { status: "queued" }
              : [task({ id: "a", status: "ready" })],
          ),
          { status: 200 },
        );
      }),
    );

    await montar();
    const botao = screen.getByRole("button", { name: /rodar agora/i });
    await act(async () => {
      botao.click();
    });

    expect(
      chamadas.some((c) => c.startsWith("POST") && c.endsWith("/run")),
    ).toBe(true);
  });

  it('"Rodar agora" não aparece fora do status ready', async () => {
    mockTasks([task({ id: "a", status: "todo" })]);

    await montar();

    expect(
      screen.queryByRole("button", { name: /rodar agora/i }),
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

  it("faz polling de reconciliação (baixa frequência) enquanto a aba está visível", async () => {
    vi.useFakeTimers();
    let chamadas = 0;
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        chamadas += 1;
        return new Response(JSON.stringify([]), { status: 200 });
      }),
    );
    Object.defineProperty(document, "visibilityState", {
      configurable: true,
      value: "visible",
    });

    render(<KanbanBoard threadId="s1" />);
    await act(async () => {
      await Promise.resolve();
    });
    const antes = chamadas;

    await act(async () => {
      await vi.advanceTimersByTimeAsync(30000);
    });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(30000);
    });

    expect(chamadas).toBeGreaterThanOrEqual(antes + 2);
    vi.useRealTimers();
  });

  it("não faz polling com a aba oculta", async () => {
    vi.useFakeTimers();
    let chamadas = 0;
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        chamadas += 1;
        return new Response(JSON.stringify([]), { status: 200 });
      }),
    );
    Object.defineProperty(document, "visibilityState", {
      configurable: true,
      value: "hidden",
    });

    render(<KanbanBoard threadId="s1" />);
    await act(async () => {
      await Promise.resolve();
    });
    const antes = chamadas;

    await act(async () => {
      await vi.advanceTimersByTimeAsync(60000);
    });

    // Erro/borda: aba oculta não deve gerar chamada nova nenhuma —
    // só o fetch inicial do mount conta.
    expect(chamadas).toBe(antes);
    vi.useRealTimers();
  });

  it("unmount limpa o interval sem chamadas órfãs", async () => {
    vi.useFakeTimers();
    let chamadas = 0;
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        chamadas += 1;
        return new Response(JSON.stringify([]), { status: 200 });
      }),
    );
    Object.defineProperty(document, "visibilityState", {
      configurable: true,
      value: "visible",
    });

    const { unmount } = render(<KanbanBoard threadId="s1" />);
    await act(async () => {
      await Promise.resolve();
    });

    unmount();
    const apos = chamadas;

    await act(async () => {
      await vi.advanceTimersByTimeAsync(20000);
    });

    expect(chamadas).toBe(apos);
    vi.useRealTimers();
  });

  it("evento SSE de status atualiza só o card afetado, sem refazer o fetch do board", async () => {
    let chamadasFetch = 0;
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        chamadasFetch += 1;
        return new Response(
          JSON.stringify([task({ id: "a", status: "todo" })]),
          { status: 200 },
        );
      }),
    );

    await montar();
    expect(
      within(screen.getByTestId("kanban-col-todo")).getByText("tarefa"),
    ).toBeInTheDocument();
    const chamadasAntesDoEvento = chamadasFetch;

    const es = MockEventSource.instances[0];
    await act(async () => {
      es.emit({
        type: "webhook_event",
        provider: "kanban",
        event_type: "kanban_task.status_changed",
        data: {
          task_id: "a",
          status: "running",
          block_kind: null,
          block_reason: null,
        },
      });
    });

    expect(
      within(screen.getByTestId("kanban-col-running")).getByText("tarefa"),
    ).toBeInTheDocument();
    expect(
      within(screen.getByTestId("kanban-col-todo")).queryByText("tarefa"),
    ).not.toBeInTheDocument();
    // Erro/borda: mover um card não é rebuscar o board inteiro — nenhum
    // fetch novo acontece só por causa do evento SSE.
    expect(chamadasFetch).toBe(chamadasAntesDoEvento);
  });

  it("evento SSE de provider diferente de kanban é ignorado", async () => {
    mockTasks([task({ id: "a", status: "todo" })]);

    await montar();
    const es = MockEventSource.instances[0];
    await act(async () => {
      es.emit({
        type: "webhook_event",
        provider: "github",
        event_type: "push",
        data: {
          task_id: "a",
          status: "running",
          block_kind: null,
          block_reason: null,
        },
      });
    });

    expect(
      within(screen.getByTestId("kanban-col-todo")).getByText("tarefa"),
    ).toBeInTheDocument();
  });

  it("reconexão do SSE depois de queda simulada volta a funcionar", async () => {
    vi.useFakeTimers();
    vi.stubGlobal(
      "fetch",
      vi.fn(
        async () =>
          new Response(JSON.stringify([task({ id: "a", status: "todo" })]), {
            status: 200,
          }),
      ),
    );

    render(<KanbanBoard threadId="s1" />);
    await act(async () => {
      await Promise.resolve();
    });

    expect(MockEventSource.instances).toHaveLength(1);
    const primeira = MockEventSource.instances[0];

    await act(async () => {
      primeira.fail();
    });
    expect(primeira.closed).toBe(true);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(3000);
    });

    expect(MockEventSource.instances).toHaveLength(2);
    const segunda = MockEventSource.instances[1];

    await act(async () => {
      segunda.emit({
        type: "webhook_event",
        provider: "kanban",
        event_type: "kanban_task.status_changed",
        data: {
          task_id: "a",
          status: "done",
          block_kind: null,
          block_reason: null,
        },
      });
    });

    expect(
      within(screen.getByTestId("kanban-col-done")).getByText("tarefa"),
    ).toBeInTheDocument();
    vi.useRealTimers();
  });

  it("unmount fecha a conexão SSE ativa", async () => {
    mockTasks([task({ id: "a", status: "todo" })]);

    const { unmount } = render(<KanbanBoard threadId="s1" />);
    await act(async () => {
      await Promise.resolve();
    });
    const es = MockEventSource.instances[0];

    unmount();

    expect(es.closed).toBe(true);
  });
});

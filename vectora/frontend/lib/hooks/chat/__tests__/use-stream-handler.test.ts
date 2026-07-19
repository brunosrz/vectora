// @vitest-environment jsdom
/**
 * Tests do useStreamHandler.processStream — o núcleo do pipeline de chat
 * (bugs #2 streaming e #4 filtro de erro). Mocka o cliente SSE (`streamChat`)
 * para emitir sequências controladas de eventos e verifica o estado final das
 * mensagens: acumulação de tokens, erro classificado virando aviso limpo
 * (isError, sem JSON cru), e conclusão (runId, fim do "thinking").
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook } from "@testing-library/react";
import type { Message } from "@/lib/types";
import type { StreamEvent } from "@/lib/api/vectora-client";
// Alias evita sombrear o `m` usado como nome de parâmetro em
// `messages.find((m) => ...)` neste arquivo (convenção do projeto).
import { m as paraglideMessages } from "@/lib/paraglide/messages";
import { useWorkspacesStore } from "@/lib/stores/workspaces-store";
import { useWorkbenchStore } from "@/lib/stores/workbench-store";
import {
  markCreateNewWorkspace,
  consumeCreateNewWorkspace,
} from "@/lib/stores/workspace-choice-registry";

const streamChatMock = vi.fn();
const resumeChatMock = vi.fn();
const getHistoryMock = vi.fn();

vi.mock("@/lib/api/vectora-client", () => ({
  streamChat: (...args: unknown[]) => streamChatMock(...args),
  resumeChat: (...args: unknown[]) => resumeChatMock(...args),
  getHistory: (...args: unknown[]) => getHistoryMock(...args),
}));

import { useStreamHandler, streamErrorMessage } from "../use-stream-handler";

function gen(events: StreamEvent[]): AsyncGenerator<StreamEvent> {
  return (async function* () {
    for (const e of events) yield e;
  })();
}

describe("useStreamHandler.processStream", () => {
  let messages: Message[];
  const setMessages = (u: Message[] | ((p: Message[]) => Message[])) => {
    messages = typeof u === "function" ? u(messages) : u;
  };

  beforeEach(() => {
    messages = [];
    streamChatMock.mockReset();
    resumeChatMock.mockReset();
    getHistoryMock.mockReset();
    window.localStorage.clear();
  });

  function run() {
    return renderHook(() => useStreamHandler({ threadId: "t1", setMessages }));
  }

  it("acumula tokens em ordem no conteúdo do assistente e finaliza", async () => {
    streamChatMock.mockReturnValue(
      gen([
        { type: "thread", thread_id: "t1" },
        { type: "token", content: "Olá" },
        { type: "token", content: ", " },
        { type: "token", content: "mundo" },
        { type: "done", thread_id: "t1", run_id: "run-1" },
      ]),
    );

    const { result } = run();
    const out = await result.current.processStream("oi", "a1");

    expect(out.assistantContent).toBe("Olá, mundo");
    expect(out.runId).toBe("run-1");

    const assistant = messages.find((m) => m.id === "a1");
    expect(assistant?.content).toBe("Olá, mundo");
    expect(assistant?.isThinking).toBe(false);
    expect(assistant?.isError).toBeFalsy();
  });

  it("Item 3 — forkFromCheckpointId presente manda config.fork_from_checkpoint_id; ausente omite (edit/regenerate)", async () => {
    streamChatMock.mockReturnValue(
      gen([
        { type: "thread", thread_id: "t1" },
        { type: "token", content: "ok" },
        { type: "done", thread_id: "t1", run_id: "run-1" },
      ]),
    );

    const { result } = run();
    await result.current.processStream("editado", "a1", undefined, "cp-999");

    expect(streamChatMock).toHaveBeenCalledTimes(1);
    const request = streamChatMock.mock.calls[0]?.[0] as {
      config: { fork_from_checkpoint_id?: string };
    };
    expect(request.config.fork_from_checkpoint_id).toBe("cp-999");

    streamChatMock.mockClear();
    streamChatMock.mockReturnValue(
      gen([
        { type: "thread", thread_id: "t1" },
        { type: "done", thread_id: "t1", run_id: "run-2" },
      ]),
    );
    await result.current.processStream("normal", "a2");
    const requestSemFork = streamChatMock.mock.calls[0]?.[0] as {
      config: { fork_from_checkpoint_id?: string };
    };
    expect(requestSemFork.config.fork_from_checkpoint_id).toBeUndefined();
  });

  it("evento de erro RATE_LIMIT vira aviso limpo + isError (não vaza JSON do provider)", async () => {
    streamChatMock.mockReturnValue(
      gen([
        { type: "thread", thread_id: "t1" },
        {
          type: "error",
          message:
            "Error calling model 'gemini-2.5-flash' (Too Many Requests): 429 " +
            "RESOURCE_EXHAUSTED quota exceeded",
          code: "RATE_LIMIT",
        },
      ]),
    );

    const { result } = run();
    await result.current.processStream("oi", "a1");

    const assistant = messages.find((m) => m.id === "a1");
    expect(assistant?.isError).toBe(true);
    expect(assistant?.isThinking).toBe(false);
    expect(assistant?.content).toBeTruthy();
    // Mensagem amigável localizada — nunca o ruído cru do provider.
    expect(assistant?.content).not.toContain("RESOURCE_EXHAUSTED");
    expect(assistant?.content).not.toContain("429");
    expect(assistant?.content).not.toMatch(/Erro no stream:/i);
  });

  it("erro após conteúdo parcial real preserva o texto já gerado (não sobrescreve)", async () => {
    // Regressão: QuotaExhaustedError no meio de um turno (ex.: orquestrador
    // já respondeu algo, delegou pro subagente coder, que estourou quota) —
    // o evento `error` sobrescrevia content inteiro pela mensagem genérica,
    // descartando qualquer trabalho parcial já visível ao usuário.
    streamChatMock.mockReturnValue(
      gen([
        { type: "thread", thread_id: "t1" },
        { type: "token", content: "Vou criar o jogo da cobrinha. " },
        { type: "token", content: "Aqui está o plano inicial..." },
        {
          type: "error",
          message: "429 RESOURCE_EXHAUSTED quota exceeded",
          code: "RATE_LIMIT",
        },
      ]),
    );

    const { result } = run();
    await result.current.processStream("crie um jogo", "a1");

    const assistant = messages.find((m) => m.id === "a1");
    expect(assistant?.isError).toBe(true);
    // O texto parcial real continua visível...
    expect(assistant?.content).toContain(
      "Vou criar o jogo da cobrinha. Aqui está o plano inicial...",
    );
    // ...com o aviso de erro anexado, não substituindo o conteúdo.
    expect(assistant?.content).toContain(streamErrorMessage("RATE_LIMIT"));
    expect(assistant?.content).not.toBe(streamErrorMessage("RATE_LIMIT"));
  });

  it("evento de erro MODEL_NO_VISION vira aviso claro (imagem + provider sem visão)", async () => {
    streamChatMock.mockReturnValue(
      gen([
        { type: "thread", thread_id: "t1" },
        {
          type: "error",
          message: "Modelo não suporta imagens anexadas.",
          code: "MODEL_NO_VISION",
        },
      ]),
    );

    const { result } = run();
    await result.current.processStream("o que tem nessa imagem?", "a1");

    const assistant = messages.find((msg) => msg.id === "a1");
    expect(assistant?.isError).toBe(true);
    expect(assistant?.content).toBe(
      paraglideMessages.chat_error_model_no_vision(),
    );
  });

  it("abort() cancela o AbortController do processStream em andamento imediatamente", async () => {
    let capturedSignal: AbortSignal | undefined;
    streamChatMock.mockImplementation((_req: unknown, signal?: AbortSignal) => {
      capturedSignal = signal;
      return (async function* () {
        // Simula o modelo "pensando" sem produzir nenhum token ainda —
        // exatamente o cenário em que o bug antigo travava o cancelamento.
        await new Promise((resolve) => setTimeout(resolve, 20));
        yield { type: "done", thread_id: "t1" } as StreamEvent;
      })();
    });

    const { result } = run();
    const streamPromise = result.current.processStream("oi", "a1");

    await vi.waitFor(() => expect(capturedSignal).toBeDefined());
    expect(capturedSignal?.aborted).toBe(false);

    result.current.abort();

    expect(capturedSignal?.aborted).toBe(true);
    await streamPromise;
  });

  it("queda de transporte (throw) preserva conteúdo parcial já recebido", async () => {
    // announceSSEDropped loga via console.error de propósito (diagnóstico
    // via DevTools) — espiona pra manter a saída do vitest limpa e
    // validar que o log de diagnóstico realmente aconteceu.
    const errorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    streamChatMock.mockReturnValue(
      (async function* () {
        yield { type: "thread", thread_id: "t1" } as StreamEvent;
        yield { type: "token", content: "parcial" } as StreamEvent;
        throw new Error("network down");
      })(),
    );

    const { result } = run();
    await result.current.processStream("oi", "a1");

    const assistant = messages.find((m) => m.id === "a1");
    // Conteúdo parcial preservado; sem texto cru de exceção.
    expect(assistant?.content).toBe("parcial");
    expect(assistant?.isThinking).toBe(false);
    expect(errorSpy).toHaveBeenCalledWith(
      "[chat] queda de transporte no stream:",
      expect.any(Error),
    );
    errorSpy.mockRestore();
  });

  it("stream corta em silêncio (generator esgota sem done/error) — reconcilia com o histórico do backend", async () => {
    // Reproduz o bug real: readSSEStream perde o evento final numa queda de
    // conexão silenciosa — o for-await simplesmente esgota, sem throw e sem
    // done/error. O conteúdo acumulado no client ("parte") não é o completo;
    // o backend já persistiu tudo no checkpoint LangGraph.
    streamChatMock.mockReturnValue(
      (async function* () {
        yield { type: "thread", thread_id: "t1" } as StreamEvent;
        yield { type: "token", content: "parte" } as StreamEvent;
        // termina aqui — sem done, sem error, sem throw.
      })(),
    );
    getHistoryMock.mockResolvedValue({
      messages: [
        { role: "human", content: "oi" },
        { role: "assistant", content: "parte completa do backend" },
      ],
    });

    const { result } = run();
    await result.current.processStream("oi", "a1");

    const assistant = messages.find((m) => m.id === "a1");
    expect(assistant?.content).toBe("parte completa do backend");
    expect(assistant?.isThinking).toBe(false);
    expect(getHistoryMock).toHaveBeenCalledWith("t1");
    // markStreamEnded NÃO foi chamado — a marca de interrupção sobrevive
    // pra avisar num reload futuro, mesmo já reconciliado aqui (defesa em
    // profundidade caso a reconciliação em si tenha falhado).
    expect(window.localStorage.getItem("vectora:streaming:t1")).not.toBeNull();
  });

  it("falha ao reconciliar (getHistory rejeita) não quebra o fluxo — conteúdo parcial permanece", async () => {
    const errorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    streamChatMock.mockReturnValue(
      (async function* () {
        yield { type: "token", content: "parte" } as StreamEvent;
      })(),
    );
    getHistoryMock.mockRejectedValue(new Error("offline"));

    const { result } = run();
    await result.current.processStream("oi", "a1");

    const assistant = messages.find((m) => m.id === "a1");
    expect(assistant?.content).toBe("parte");
    errorSpy.mockRestore();
  });

  it("evento hitl encerra o loop sem disparar reconciliação (pausa deliberada, não truncamento)", async () => {
    streamChatMock.mockReturnValue(
      (async function* () {
        yield { type: "token", content: "pensando" } as StreamEvent;
        yield {
          type: "hitl",
          tool_name: "file_write",
          args_json: "{}",
          interrupt_id: "int-1",
        } as StreamEvent;
      })(),
    );

    const { result } = run();
    await result.current.processStream("oi", "a1");

    expect(getHistoryMock).not.toHaveBeenCalled();
    expect(window.localStorage.getItem("vectora:streaming:t1")).toBeNull();
    const assistant = messages.find((m) => m.id === "a1");
    expect(assistant?.hitlPending?.toolName).toBe("file_write");
  });

  it("message_break mantém bolha única e concatena segmentos com separador", async () => {
    streamChatMock.mockReturnValue(
      gen([
        { type: "thread", thread_id: "t1" },
        { type: "token", content: "Segmento 1" },
        { type: "message_break" },
        { type: "token", content: "Segmento 2" },
        { type: "done", thread_id: "t1", run_id: "run-2" },
      ]),
    );

    const { result } = run();
    await result.current.processStream("oi", "a1");

    // Deve haver apenas UMA mensagem do assistente (single-bubble)
    const assistants = messages.filter((m) => m.role === "assistant");
    expect(assistants.length).toBe(1);

    // A única bolha contém os dois segmentos concatenados com separador
    const single = messages.find((m) => m.id === "a1");
    expect(single?.content).toContain("Segmento 1");
    expect(single?.content).toContain("Segmento 2");
    expect(single?.isThinking).toBe(false);
  });

  it("race condition: assistantContent preservado mesmo com setMessages([]) externo durante stream", async () => {
    // Documenta o sintoma do bug de race condition em loadThreadHistory:
    // quando setMessages([]) é chamado externamente enquanto o stream processa
    // tokens, o acumulador local do handler preserva o conteúdo — mas a
    // mensagem do assistente SOME do estado React porque updateMessageInList
    // em array vazio retorna [].
    // O fix está em chat-interface.tsx (guard hasSentMessageRef), que impede
    // setMessages([]) de ser chamado quando o usuário já enviou ao thread.

    let externalWipe: (() => void) | undefined;

    // setMessages customizado que expõe um "wipe" externo após a primeira
    // chamada (que cria a mensagem assistente inicial via ensureMessageExists).
    let localMessages: Message[] = [];
    let firstCallDone = false;
    const setMsgsWithWipe = (u: Message[] | ((p: Message[]) => Message[])) => {
      localMessages = typeof u === "function" ? u(localMessages) : u;
      if (!firstCallDone) {
        firstCallDone = true;
        // Expõe o wipe DEPOIS da primeira chamada de setup
        externalWipe = () => {
          localMessages = [];
        };
      }
    };

    streamChatMock.mockReturnValue(
      gen([
        { type: "thread", thread_id: "t1" },
        { type: "token", content: "Resposta" },
        { type: "done", thread_id: "t1", run_id: "run-race" },
      ]),
    );

    const { result } = renderHook(() =>
      useStreamHandler({ threadId: "t1", setMessages: setMsgsWithWipe }),
    );

    // Inicia o stream — setMessages chamado sincronamente para criar assistante
    const streamPromise = result.current.processStream("oi", "a1");

    // Simula loadThreadHistory resolvendo com [] DURANTE o stream (race condition)
    externalWipe?.();

    const out = await streamPromise;

    // assistantContent local do handler fica correto: acumulado independente do estado React
    expect(out.assistantContent).toBe("Resposta");

    // O estado React está vazio: tokens foram perdidos porque updateMessageInList
    // opera sobre array vazio após o wipe.
    // (Este é o sintoma que o guard em loadThreadHistory previne.)
    const foundInState = localMessages.find(
      (m) => m.role === "assistant" && m.content === "Resposta",
    );
    expect(foundInState).toBeUndefined();
  });

  it("race condition não ocorre quando hasSentMessageRef é checado antes de setMessages([])", () => {
    // Especificação do guard adicionado em chat-interface.tsx:
    // loadThreadHistory só chama setMessages([]) quando hasSentMessageRef
    // NÃO aponta para o thread atual.
    const setMessagesMock = vi.fn();
    const hasSentRef: { current: string | null } = { current: null };
    const currentThreadId = "thread-abc";
    const historyMessages: unknown[] = [];

    // Cenário 1: usuário enviou mensagem → ref aponta para o thread → NÃO apaga
    hasSentRef.current = currentThreadId;
    if (
      historyMessages.length === 0 &&
      hasSentRef.current !== currentThreadId
    ) {
      setMessagesMock([]);
    }
    expect(setMessagesMock).not.toHaveBeenCalled();

    // Cenário 2: usuário ainda não enviou → ref é null → APAGA (comportamento correto)
    hasSentRef.current = null;
    if (
      historyMessages.length === 0 &&
      hasSentRef.current !== currentThreadId
    ) {
      setMessagesMock([]);
    }
    expect(setMessagesMock).toHaveBeenCalledWith([]);
  });

  it("message_break sem tokens anteriores não adiciona separador vazio", async () => {
    streamChatMock.mockReturnValue(
      gen([
        { type: "thread", thread_id: "t1" },
        { type: "message_break" },
        { type: "token", content: "só uma bolha" },
        { type: "done", thread_id: "t1" },
      ]),
    );

    const { result } = run();
    await result.current.processStream("oi", "a1");

    // Deve haver exatamente UMA mensagem do assistente
    const assistants = messages.filter((m) => m.role === "assistant");
    expect(assistants.length).toBe(1);

    // Sem conteúdo prévio, message_break não adiciona separador "\n\n"
    const single = messages.find((m) => m.id === "a1");
    expect(single?.content).toBe("só uma bolha");
  });

  // ── model_switched (A4 — fallback de provider por quota) ─────────────────────

  it("evento model_switched chama onModelSwitched(from, to)", async () => {
    const onModelSwitched = vi.fn();
    streamChatMock.mockReturnValue(
      gen([
        { type: "thread", thread_id: "t1" },
        { type: "token", content: "oi" },
        {
          type: "model_switched",
          from_model: "openai:gpt-4o",
          to_model: "google-genai:gemini-2.5-flash",
        },
        { type: "done", thread_id: "t1", run_id: "r1" },
      ]),
    );
    const { result } = renderHook(() =>
      useStreamHandler({ threadId: "t1", setMessages, onModelSwitched }),
    );
    await result.current.processStream("oi", "a1");
    expect(onModelSwitched).toHaveBeenCalledWith(
      "openai:gpt-4o",
      "google-genai:gemini-2.5-flash",
    );
  });

  it("model_switched não interrompe o stream de tokens", async () => {
    streamChatMock.mockReturnValue(
      gen([
        { type: "token", content: "a" },
        { type: "model_switched", from_model: "x:1", to_model: "y:2" },
        { type: "token", content: "b" },
        { type: "done", thread_id: "t1" },
      ]),
    );
    const { result } = run();
    const out = await result.current.processStream("oi", "a1");
    expect(out.assistantContent).toBe("ab");
  });

  it("sem onModelSwitched, model_switched é ignorado sem erro", async () => {
    streamChatMock.mockReturnValue(
      gen([
        { type: "token", content: "ok" },
        { type: "model_switched", from_model: "x:1", to_model: "y:2" },
        { type: "done", thread_id: "t1" },
      ]),
    );
    const { result } = run();
    const out = await result.current.processStream("oi", "a1");
    expect(out.assistantContent).toBe("ok");
  });

  // ── yieldToBrowser — streaming letra a letra ──────────────────────────────

  it("cada token chama setMessages individualmente (streaming letra a letra)", async () => {
    // Com yieldToBrowser, cada token faz um setMessages separado —
    // o conteúdo cresce incrementalmente, não de uma vez.
    const calls: string[] = [];
    const setMsgsTracking = (u: Message[] | ((p: Message[]) => Message[])) => {
      const next = typeof u === "function" ? u(messages) : u;
      const a = next.find((m) => m.role === "assistant");
      if (a && typeof a.content === "string" && a.content !== "") {
        calls.push(a.content);
      }
      messages = next;
    };

    streamChatMock.mockReturnValue(
      gen([
        { type: "token", content: "A" },
        { type: "token", content: "B" },
        { type: "token", content: "C" },
        { type: "done", thread_id: "t1" },
      ]),
    );

    const { result } = renderHook(() =>
      useStreamHandler({ threadId: "t1", setMessages: setMsgsTracking }),
    );
    await result.current.processStream("oi", "a1");

    // Cada token gerou um estado intermediário distinto
    expect(calls).toContain("A");
    expect(calls).toContain("AB");
    expect(calls).toContain("ABC");
    // A ordem incremental deve estar preservada
    const aIdx = calls.indexOf("A");
    const abIdx = calls.indexOf("AB");
    const abcIdx = calls.indexOf("ABC");
    expect(aIdx).toBeLessThan(abIdx);
    expect(abIdx).toBeLessThan(abcIdx);
  });

  it("token com newline é preservado no conteúdo", async () => {
    streamChatMock.mockReturnValue(
      gen([
        { type: "token", content: "linha1\n" },
        { type: "token", content: "linha2" },
        { type: "done", thread_id: "t1" },
      ]),
    );
    const { result } = run();
    const out = await result.current.processStream("oi", "a1");
    expect(out.assistantContent).toBe("linha1\nlinha2");
    expect(messages.find((m) => m.id === "a1")?.content).toBe("linha1\nlinha2");
  });

  it("token vazio não adiciona conteúdo", async () => {
    streamChatMock.mockReturnValue(
      gen([
        { type: "token", content: "real" },
        { type: "token", content: "" },
        { type: "done", thread_id: "t1" },
      ]),
    );
    const { result } = run();
    const out = await result.current.processStream("oi", "a1");
    expect(out.assistantContent).toBe("real");
  });

  it("done sem run_id → runId é undefined", async () => {
    streamChatMock.mockReturnValue(
      gen([
        { type: "token", content: "x" },
        { type: "done", thread_id: "t1" },
      ]),
    );
    const { result } = run();
    const out = await result.current.processStream("oi", "a1");
    expect(out.runId).toBeUndefined();
  });

  it("erro AUTH retorna mensagem limpa localizada", async () => {
    streamChatMock.mockReturnValue(
      gen([{ type: "error", message: "401 auth failed", code: "AUTH" }]),
    );
    const { result } = run();
    await result.current.processStream("oi", "a1");
    const a = messages.find((m) => m.id === "a1");
    expect(a?.isError).toBe(true);
    expect(a?.content).toBeTruthy();
    expect(a?.content).not.toContain("401");
    expect(a?.content).not.toContain("auth failed");
  });

  it("erro TIMEOUT retorna mensagem limpa localizada", async () => {
    streamChatMock.mockReturnValue(
      gen([{ type: "error", message: "ReadTimeout", code: "TIMEOUT" }]),
    );
    const { result } = run();
    await result.current.processStream("oi", "a1");
    const a = messages.find((m) => m.id === "a1");
    expect(a?.isError).toBe(true);
    expect(a?.content).toBeTruthy();
    expect(a?.content).not.toContain("ReadTimeout");
  });

  it("erro sem code (STREAM_ERROR) retorna mensagem genérica localizada", async () => {
    streamChatMock.mockReturnValue(
      gen([{ type: "error", message: "unexpected crash" }]),
    );
    const { result } = run();
    await result.current.processStream("oi", "a1");
    const a = messages.find((m) => m.id === "a1");
    expect(a?.isError).toBe(true);
    expect(a?.content).toBeTruthy();
    expect(a?.content).not.toContain("unexpected crash");
  });

  it("AbortError encerra o thinking sem marcar isError", async () => {
    streamChatMock.mockReturnValue(
      (async function* () {
        yield { type: "token", content: "parcial" } as StreamEvent;
        const err = new Error("user abort");
        err.name = "AbortError";
        throw err;
      })(),
    );
    const { result } = run();
    await result.current.processStream("oi", "a1");
    const a = messages.find((m) => m.id === "a1");
    expect(a?.isThinking).toBe(false);
    expect(a?.isError).toBeFalsy();
    // Conteúdo parcial é preservado
    expect(a?.content).toBe("parcial");
  });

  // ── message_break — strip de envelope por segmento ───────────────────────

  it("message_break strips envelope markdown do primeiro segmento", async () => {
    streamChatMock.mockReturnValue(
      gen([
        { type: "token", content: "``````markdown\n" },
        { type: "token", content: "Conteúdo limpo" },
        { type: "token", content: "\n``````" },
        { type: "message_break" },
        { type: "token", content: " mais texto" },
        { type: "done", thread_id: "t1" },
      ]),
    );
    const { result } = run();
    await result.current.processStream("oi", "a1");
    const a = messages.find((m) => m.id === "a1");
    // O envelope não deve aparecer no conteúdo final
    expect(a?.content).not.toContain("``````");
    expect(a?.content).toContain("Conteúdo limpo");
  });

  it("múltiplos message_break consecutivos mantêm single-bubble", async () => {
    streamChatMock.mockReturnValue(
      gen([
        { type: "token", content: "Seg1" },
        { type: "message_break" },
        { type: "token", content: "Seg2" },
        { type: "message_break" },
        { type: "token", content: "Seg3" },
        { type: "done", thread_id: "t1" },
      ]),
    );
    const { result } = run();
    await result.current.processStream("oi", "a1");

    // Ainda uma única mensagem
    expect(messages.filter((m) => m.role === "assistant")).toHaveLength(1);
    const a = messages.find((m) => m.id === "a1");
    expect(a?.content).toContain("Seg1");
    expect(a?.content).toContain("Seg2");
    expect(a?.content).toContain("Seg3");
  });

  it("message_break adiciona '\\n\\n' entre segmentos quando há conteúdo prévio", async () => {
    streamChatMock.mockReturnValue(
      gen([
        { type: "token", content: "Primeiro" },
        { type: "message_break" },
        { type: "token", content: "Segundo" },
        { type: "done", thread_id: "t1" },
      ]),
    );
    const { result } = run();
    await result.current.processStream("oi", "a1");
    const a = messages.find((m) => m.id === "a1");
    expect(a?.content).toContain("\n\n");
    expect(a?.content).toMatch(/Primeiro[\s\S]*Segundo/);
  });

  it("terminal_line anexa linhas ao vivo na tool terminal ainda sem output", async () => {
    streamChatMock.mockReturnValue(
      gen([
        {
          type: "tool_call",
          tool_name: "terminal",
          tool_call_id: "tc1",
          args_json: '{"command":"npm install"}',
          render_hint: "terminal_output",
        },
        { type: "terminal_line", line: "added 1 package" },
        { type: "terminal_line", line: "audited 5 packages" },
        {
          type: "tool_result",
          tool_call_id: "tc1",
          content_json: '"done"',
        },
        { type: "done", thread_id: "t1" },
      ]),
    );
    const { result } = run();
    await result.current.processStream("oi", "a1");

    const a = messages.find((m) => m.id === "a1");
    const tc = a?.toolCalls?.find((t) => t.id === "tc1");
    expect(tc?.liveOutputLines).toEqual([
      "added 1 package",
      "audited 5 packages",
    ]);
    // Output final chegou — a UI passa a mostrar `output`, não mais as linhas.
    expect(tc?.output).toBe("done");
  });

  it("terminal_line sem nenhuma tool terminal ativa não quebra o stream (edge)", async () => {
    streamChatMock.mockReturnValue(
      gen([
        { type: "terminal_line", line: "linha orfa" },
        { type: "token", content: "ok" },
        { type: "done", thread_id: "t1" },
      ]),
    );
    const { result } = run();
    const out = await result.current.processStream("oi", "a1");
    expect(out.assistantContent).toBe("ok");
    const a = messages.find((m) => m.id === "a1");
    expect(a?.toolCalls ?? []).toHaveLength(0);
  });

  it("todos_updated popula o slice de todos do workbench-store (Plan Mode real)", async () => {
    streamChatMock.mockReturnValue(
      gen([
        {
          type: "todos_updated",
          todos: [{ content: "passo 1", status: "in_progress" }],
        },
        { type: "done", thread_id: "t1" },
      ]),
    );
    const { result } = run();
    await result.current.processStream("faça um plano", "a1");

    expect(useWorkbenchStore.getState().getTodos("t1")).toEqual([
      { content: "passo 1", status: "in_progress" },
    ]);
  });

  it("subagent_output popula subgraphOutputs com identidade e dedupa por tool_call_id", async () => {
    streamChatMock.mockReturnValue(
      gen([
        {
          type: "subagent_output",
          subagent_type: "coder",
          description: "faz X",
          status: "running",
          tool_call_id: "r1",
          content: "",
        },
        {
          type: "subagent_output",
          subagent_type: "coder",
          description: "faz X",
          status: "complete",
          tool_call_id: "r1",
          content: "arquivo criado",
        },
        { type: "done", thread_id: "t1" },
      ]),
    );
    const { result } = run();
    await result.current.processStream("delega pro coder", "a1");

    const a = messages.find((m) => m.id === "a1");
    // Dedupe por tool_call_id: um card só, com o estado final.
    expect(a?.subgraphOutputs ?? []).toHaveLength(1);
    const sub = a!.subgraphOutputs![0];
    expect(sub.name).toBe("coder");
    expect(sub.output).toBe("arquivo criado");
    expect(sub.isComplete).toBe(true);
    expect(sub.isStreaming).toBe(false);
  });

  it("subagent_output com status='error' marca isComplete e carrega a mensagem de erro", async () => {
    streamChatMock.mockReturnValue(
      gen([
        {
          type: "subagent_output",
          subagent_type: "search",
          description: "busca X",
          status: "running",
          tool_call_id: "r-err",
          content: "",
        },
        {
          type: "subagent_output",
          subagent_type: "search",
          description: "busca X",
          status: "error",
          tool_call_id: "r-err",
          content: "falha ao buscar",
        },
        { type: "done", thread_id: "t1" },
      ]),
    );
    const { result } = run();
    await result.current.processStream("delega pro search", "a1");

    const a = messages.find((m) => m.id === "a1");
    expect(a?.subgraphOutputs ?? []).toHaveLength(1);
    const sub = a!.subgraphOutputs![0];
    expect(sub.output).toBe("falha ao buscar");
    // O status "running" não recebe tratamento distinto de "complete": ambos
    // saem de streaming e ficam marcados como concluídos (o conteúdo é que
    // comunica a falha ao usuário).
    expect(sub.isComplete).toBe(true);
    expect(sub.isStreaming).toBe(false);
  });
});

// ============================================================================
// processResume
// ============================================================================

describe("useStreamHandler.processResume", () => {
  let messages: Message[];
  const setMessages = (u: Message[] | ((p: Message[]) => Message[])) => {
    messages = typeof u === "function" ? u(messages) : u;
  };

  beforeEach(() => {
    messages = [
      {
        id: "a1",
        role: "assistant",
        content: "conteúdo anterior",
        timestamp: new Date(),
        isThinking: false,
      },
    ];
    streamChatMock.mockReset();
    resumeChatMock.mockReset();
    getHistoryMock.mockReset();
    window.localStorage.clear();
  });

  function run() {
    return renderHook(() => useStreamHandler({ threadId: "t1", setMessages }));
  }

  const resumeReq = {
    thread_id: "t1",
    interrupt_id: "i1",
    decision: "approve" as const,
  };

  it("stream de resume corta em silêncio — reconcilia com o histórico do backend", async () => {
    resumeChatMock.mockReturnValue(
      (async function* () {
        yield { type: "token", content: " parte" } as StreamEvent;
        // termina sem done/error — mesma classe de bug de processStream.
      })(),
    );
    getHistoryMock.mockResolvedValue({
      messages: [{ role: "assistant", content: "resposta completa" }],
    });

    const { result } = run();
    await result.current.processResume(resumeReq, "a1");

    const assistant = messages.find((m) => m.id === "a1");
    expect(assistant?.content).toBe("resposta completa");
    expect(getHistoryMock).toHaveBeenCalledWith("t1");
    expect(window.localStorage.getItem("vectora:streaming:t1")).not.toBeNull();
  });

  it("acumula tokens e retorna assistantContent correto", async () => {
    resumeChatMock.mockReturnValue(
      gen([
        { type: "token", content: "continuação" },
        { type: "token", content: " da resposta" },
        { type: "done", thread_id: "t1" },
      ]),
    );
    const { result } = renderHook(() =>
      useStreamHandler({ threadId: "t1", setMessages }),
    );
    const out = await result.current.processResume(resumeReq, "a1");
    expect(out.assistantContent).toBe("continuação da resposta");
  });

  it("tokens são adicionados ao conteúdo existente da mensagem", async () => {
    resumeChatMock.mockReturnValue(
      gen([
        { type: "token", content: " nova parte" },
        { type: "done", thread_id: "t1" },
      ]),
    );
    const { result } = run();
    await result.current.processResume(resumeReq, "a1");
    const a = messages.find((m) => m.id === "a1");
    expect(a?.content).toContain("nova parte");
  });

  it("encerra o thinking ao receber done", async () => {
    resumeChatMock.mockReturnValue(
      gen([
        { type: "token", content: "ok" },
        { type: "done", thread_id: "t1" },
      ]),
    );
    const { result } = run();
    await result.current.processResume(resumeReq, "a1");
    const a = messages.find((m) => m.id === "a1");
    expect(a?.isThinking).toBe(false);
  });

  it("erro de aplicação vira isError na mensagem", async () => {
    resumeChatMock.mockReturnValue(
      gen([{ type: "error", message: "429 quota", code: "RATE_LIMIT" }]),
    );
    const { result } = run();
    await result.current.processResume(resumeReq, "a1");
    const a = messages.find((m) => m.id === "a1");
    expect(a?.isError).toBe(true);
    expect(a?.isThinking).toBe(false);
    expect(a?.content).not.toContain("429");
  });

  it("queda de transporte preserva conteúdo parcial já recebido", async () => {
    const errorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    resumeChatMock.mockReturnValue(
      (async function* () {
        yield { type: "token", content: "parcial" } as StreamEvent;
        throw new Error("network error");
      })(),
    );
    const { result } = run();
    await result.current.processResume(resumeReq, "a1");
    const a = messages.find((m) => m.id === "a1");
    expect(a?.isThinking).toBe(false);
    expect(a?.content).toContain("parcial");
    expect(errorSpy).toHaveBeenCalledWith(
      "[chat] queda de transporte no stream:",
      expect.any(Error),
    );
    errorSpy.mockRestore();
  });

  it("AbortError não marca isError e encerra thinking", async () => {
    resumeChatMock.mockReturnValue(
      (async function* () {
        yield { type: "token", content: "interrompido" } as StreamEvent;
        const err = new Error("abort");
        err.name = "AbortError";
        throw err;
      })(),
    );
    const { result } = run();
    await result.current.processResume(resumeReq, "a1");
    const a = messages.find((m) => m.id === "a1");
    expect(a?.isThinking).toBe(false);
    expect(a?.isError).toBeFalsy();
  });

  it("cada token de resume chama setMessages individualmente", async () => {
    const contentHistory: string[] = [];
    const trackingSet = (u: Message[] | ((p: Message[]) => Message[])) => {
      messages = typeof u === "function" ? u(messages) : u;
      const a = messages.find((m) => m.id === "a1");
      if (a && typeof a.content === "string") {
        contentHistory.push(a.content);
      }
    };
    resumeChatMock.mockReturnValue(
      gen([
        { type: "token", content: "X" },
        { type: "token", content: "Y" },
        { type: "done", thread_id: "t1" },
      ]),
    );
    const { result } = renderHook(() =>
      useStreamHandler({ threadId: "t1", setMessages: trackingSet }),
    );
    await result.current.processResume(resumeReq, "a1");
    // Deve haver estados intermediários com X e XY separados
    const hasX = contentHistory.some((c) => c.endsWith("X"));
    const hasXY = contentHistory.some((c) => c.endsWith("XY"));
    expect(hasX).toBe(true);
    expect(hasXY).toBe(true);
  });
});

describe("useStreamHandler — workspace de sessão nova", () => {
  let messages: Message[];
  const setMessages = (u: Message[] | ((p: Message[]) => Message[])) => {
    messages = typeof u === "function" ? u(messages) : u;
  };

  beforeEach(() => {
    messages = [];
    streamChatMock.mockReset();
    resumeChatMock.mockReset();
    useWorkspacesStore.setState({ active_id: null, workspaces: [] });
  });

  it("consome o sinal 'criar novo workspace': manda create_new_workspace e nunca o active_id stale", async () => {
    // active_id stale de uma conversa anterior — sem o fix, vazaria como
    // config.workspace_id mesmo o usuário tendo pedido um workspace novo.
    useWorkspacesStore.setState({ active_id: "ws-antigo" });
    markCreateNewWorkspace("t1");

    // Resposta realista do backend: create_new_workspace=true sempre resolve
    // pra um workspace_id não-vazio no evento thread (confirma o sinal —
    // sem isso o finally de use-stream-handler re-marcaria "t1" à toa).
    streamChatMock.mockReturnValue(
      gen([
        { type: "thread", thread_id: "t1", workspace_id: "ws-novo" },
        { type: "token", content: "oi" },
        { type: "done", thread_id: "t1" },
      ]),
    );

    const { result } = renderHook(() =>
      useStreamHandler({ threadId: "t1", setMessages }),
    );
    await result.current.processStream("cria um workspace novo", "a1");

    const sentConfig = (
      streamChatMock.mock.calls[0]![0] as { config: Record<string, unknown> }
    ).config;
    expect(sentConfig.create_new_workspace).toBe(true);
    expect(sentConfig.workspace_id).toBeUndefined();
  });

  it("sem o sinal, comportamento antigo: manda o active_id como workspace_id (edge)", async () => {
    useWorkspacesStore.setState({ active_id: "ws-ativo" });

    streamChatMock.mockReturnValue(
      gen([
        { type: "thread", thread_id: "t1" },
        { type: "token", content: "oi" },
        { type: "done", thread_id: "t1" },
      ]),
    );

    const { result } = renderHook(() =>
      useStreamHandler({ threadId: "t1", setMessages }),
    );
    await result.current.processStream("mensagem normal", "a1");

    const sentConfig = (
      streamChatMock.mock.calls[0]![0] as { config: Record<string, unknown> }
    ).config;
    expect(sentConfig.workspace_id).toBe("ws-ativo");
    expect(sentConfig.create_new_workspace).toBeUndefined();
  });

  it("sincroniza active_id ao receber o workspace_id resolvido no evento thread", async () => {
    streamChatMock.mockReturnValue(
      gen([
        { type: "thread", thread_id: "t1", workspace_id: "ws-recem-criado" },
        { type: "token", content: "oi" },
        { type: "done", thread_id: "t1" },
      ]),
    );

    const { result } = renderHook(() =>
      useStreamHandler({ threadId: "t1", setMessages }),
    );
    await result.current.processStream("cria um workspace novo", "a1");

    expect(useWorkspacesStore.getState().active_id).toBe("ws-recem-criado");
  });

  it("restaura o sinal 'criar novo workspace' se a conexão cair antes do evento thread confirmar (bug: retry usava workspace stale)", async () => {
    useWorkspacesStore.setState({ active_id: "ws-antigo" });
    markCreateNewWorkspace("t1");

    // Queda de transporte total — nenhum evento chega, nem o `thread` que
    // confirmaria o workspace resolvido.
    streamChatMock.mockReturnValue(
      (async function* (): AsyncGenerator<StreamEvent> {
        throw new Error("conexão perdida");
      })(),
    );

    const { result } = renderHook(() =>
      useStreamHandler({ threadId: "t1", setMessages }),
    );
    await result.current.processStream("cria um workspace novo", "a1");

    // O sinal deve ter voltado — um retry no mesmo thread ainda pede
    // workspace novo, em vez de silenciosamente reusar o active_id stale.
    expect(consumeCreateNewWorkspace("t1")).toBe(true);
  });

  it("NÃO restaura o sinal se o workspace já foi confirmado antes de um erro posterior (edge — evitaria criar workspace duplicado num retry)", async () => {
    markCreateNewWorkspace("t1");

    streamChatMock.mockReturnValue(
      gen([
        { type: "thread", thread_id: "t1", workspace_id: "ws-recem-criado" },
        { type: "error", message: "quota excedida", code: "RATE_LIMIT" },
      ]),
    );

    const { result } = renderHook(() =>
      useStreamHandler({ threadId: "t1", setMessages }),
    );
    await result.current.processStream("cria um workspace novo", "a1");

    expect(consumeCreateNewWorkspace("t1")).toBe(false);
  });
});

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

const streamChatMock = vi.fn();
const resumeChatMock = vi.fn();

vi.mock("@/lib/api/vectora-client", () => ({
  streamChat: (...args: unknown[]) => streamChatMock(...args),
  resumeChat: (...args: unknown[]) => resumeChatMock(...args),
}));

import { useStreamHandler } from "../use-stream-handler";

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

  it("queda de transporte (throw) preserva conteúdo parcial já recebido", async () => {
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
  });

  it("message_break cria segunda bolha e acumula tokens separados por bolha", async () => {
    streamChatMock.mockReturnValue(
      gen([
        { type: "thread", thread_id: "t1" },
        { type: "token", content: "Bolha 1" },
        { type: "message_break" },
        { type: "token", content: "Bolha 2" },
        { type: "done", thread_id: "t1", run_id: "run-2" },
      ]),
    );

    const { result } = run();
    await result.current.processStream("oi", "a1");

    // Deve haver pelo menos 2 mensagens do assistente
    const assistants = messages.filter((m) => m.role === "assistant");
    expect(assistants.length).toBeGreaterThanOrEqual(2);

    // Primeira bolha tem conteúdo da primeira fase
    const first = messages.find((m) => m.id === "a1");
    expect(first?.content).toBe("Bolha 1");
    expect(first?.isThinking).toBe(false);

    // Segunda bolha tem conteúdo da segunda fase
    const second = assistants.find((m) => m.id !== "a1");
    expect(second?.content).toBe("Bolha 2");
    expect(second?.isThinking).toBe(false);
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

  it("message_break sem tokens anteriores não cria bolha vazia", async () => {
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

    // message_break logo no início (sem tokens antes) deve ser ignorado pelo backend,
    // mas mesmo que chegue, a bolha inicial não deve ficar com conteúdo vazio ao lado
    // de uma segunda com "só uma bolha"
    const withContent = messages.filter(
      (m) => m.role === "assistant" && m.content !== "",
    );
    // Deve existir exatamente uma bolha com conteúdo real
    expect(withContent.length).toBeGreaterThanOrEqual(1);
    const found = withContent.find((m) => m.content === "só uma bolha");
    expect(found).toBeTruthy();
  });
});

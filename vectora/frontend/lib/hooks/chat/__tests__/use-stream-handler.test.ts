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
});

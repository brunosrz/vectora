// @vitest-environment jsdom
/**
 * MessageList — troca de thread não pode deixar o usuário ver o scroll
 * "perseguindo" o fim da conversa: o conteúdo fica visibility:hidden
 * enquanto o polling de convergência de scrollHeight ainda está rodando,
 * e só é revelado quando estabiliza (ou quando o cap de segurança expira).
 */

import { describe, expect, it, afterEach, vi } from "vitest";
import { act, render, screen, cleanup } from "@testing-library/react";
import { MessageList } from "../message-list";
import type { Message } from "@/lib/types";

vi.mock("../message-item", () => ({
  MessageItem: ({ message }: { message: Message }) => (
    <div data-testid="message-item">{message.content}</div>
  ),
}));

vi.mock("../message-skeleton", () => ({
  MessageSkeletons: () => <div data-testid="message-skeletons" />,
}));

const { scrollToIndexMock } = vi.hoisted(() => ({
  scrollToIndexMock: vi.fn(),
}));

// Thread virtualizada (> VIRTUALIZE_THRESHOLD mensagens): escrever
// scrollTop direto no container não é confiável com @tanstack/react-virtual
// (ele mantém seu próprio offset interno) — precisa passar por
// scrollToIndex. Mock leve só pra espionar essa chamada; getVirtualItems
// vazio é suficiente porque os testes abaixo não afirmam nada sobre quais
// itens renderizam, só que o scroll converge para o índice certo.
vi.mock("@tanstack/react-virtual", () => ({
  useVirtualizer: () => ({
    getVirtualItems: () => [],
    getTotalSize: () => 20000,
    scrollToIndex: scrollToIndexMock,
    measureElement: () => {},
  }),
}));

// jsdom não implementa Element.scrollTo — o efeito de auto-scroll durante
// streaming (message-list.tsx) chama isso incondicionalmente no mount.
const noopScrollTo = () => {};
if (!Element.prototype.scrollTo) {
  Element.prototype.scrollTo = noopScrollTo;
}

afterEach(() => {
  cleanup();
  vi.useRealTimers();
  scrollToIndexMock.mockClear();
});

function msg(id: string, content: string): Message {
  return {
    id,
    role: "assistant",
    content,
    timestamp: new Date(),
  } as unknown as Message;
}

function baseProps(messages: Message[]) {
  return {
    messages,
    isRegenerating: false,
    copiedId: null,
    onCopy: vi.fn(),
    onRegenerate: vi.fn(),
    feedbackComment: {},
    showCommentInput: null,
    onFeedback: vi.fn(),
    onSubmitComment: vi.fn(),
    onCancelComment: vi.fn(),
    onToggleComment: vi.fn(),
    setFeedbackComment: vi.fn(),
  };
}

/** Instala um scrollHeight que cresce por algumas leituras e depois
 * estabiliza (simula o conteúdo real medindo/montando aos poucos). */
function mockConvergingScrollHeight(container: HTMLElement) {
  let reads = 0;
  Object.defineProperty(container, "scrollHeight", {
    configurable: true,
    get: () => {
      reads++;
      return reads < 10 ? 1000 + reads * 50 : 2000;
    },
  });
  Object.defineProperty(container, "clientHeight", {
    configurable: true,
    get: () => 500,
  });
}

/** Instala um scrollHeight que nunca para de crescer — prova o cap.
 * Devolve um contador vivo de leituras, pra provar que o polling parou de
 * verdade (não só a UI parou de esconder o conteúdo). */
function mockNeverConvergingScrollHeight(container: HTMLElement): {
  count: number;
} {
  const reads = { count: 0 };
  Object.defineProperty(container, "scrollHeight", {
    configurable: true,
    get: () => {
      reads.count++;
      return 1000 + reads.count * 50;
    },
  });
  Object.defineProperty(container, "clientHeight", {
    configurable: true,
    get: () => 500,
  });
  return reads;
}

describe("MessageList — scroll settling na troca de thread", () => {
  it("esconde o conteúdo enquanto o scroll converge e revela quando estabiliza", async () => {
    vi.useFakeTimers();
    render(<MessageList {...baseProps([msg("m1", "olá")])} />);

    const container = screen.getByLabelText("Messages");
    mockConvergingScrollHeight(container);

    const content = screen.getByTestId("message-list-content");
    expect(content).toHaveStyle({ visibility: "hidden" });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(3000);
    });

    expect(content).toHaveStyle({ visibility: "visible" });
  });

  it("caso de borda: se o scrollHeight nunca estabiliza, o cap de segurança revela o conteúdo E desarma o polling", async () => {
    vi.useFakeTimers();
    render(<MessageList {...baseProps([msg("m1", "olá")])} />);

    const container = screen.getByLabelText("Messages");
    const reads = mockNeverConvergingScrollHeight(container);

    const content = screen.getByTestId("message-list-content");
    expect(content).toHaveStyle({ visibility: "hidden" });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1600);
    });

    expect(content).toHaveStyle({ visibility: "visible" });

    // O cap não pode só esconder/revelar visualmente — precisa desarmar o
    // polling (MutationObserver + isAutoScrollingRef) também, senão ele
    // continua brigando por scroll em segundo plano por mais ~8,5s (até o
    // teto de MAX_SCROLL_ATTEMPTS). Sem o polling rodando, mais nenhuma
    // leitura de scrollHeight deveria acontecer.
    const readsAtCap = reads.count;
    await act(async () => {
      await vi.advanceTimersByTimeAsync(3000);
    });
    expect(reads.count).toBe(readsAtCap);
  });

  it("não reesconde o conteúdo quando a thread não muda (ex.: nova mensagem chegando via streaming)", async () => {
    vi.useFakeTimers();
    const { rerender } = render(
      <MessageList {...baseProps([msg("m1", "olá")])} />,
    );

    const container = screen.getByLabelText("Messages");
    mockConvergingScrollHeight(container);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(3000);
    });

    const content = screen.getByTestId("message-list-content");
    expect(content).toHaveStyle({ visibility: "visible" });

    rerender(
      <MessageList
        {...baseProps([msg("m1", "olá"), msg("m2", "segunda mensagem")])}
      />,
    );

    expect(content).toHaveStyle({ visibility: "visible" });
  });
});

describe("MessageList — thread virtualizada (> 50 mensagens)", () => {
  it("usa virtualizer.scrollToIndex pro último item, não scrollTop bruto", async () => {
    vi.useFakeTimers();
    const manyMessages = Array.from({ length: 80 }, (_, i) =>
      msg(`m${i}`, `mensagem ${i}`),
    );
    render(<MessageList {...baseProps(manyMessages)} />);

    const container = screen.getByLabelText("Messages");
    mockConvergingScrollHeight(container);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(3000);
    });

    // O efeito de streaming também chama scrollToIndex uma vez no mount
    // (mensagem "nova" do zero) — isso sozinho não prova nada sobre o
    // polling de convergência da troca de thread. A prova real é o
    // polling repetido (scrollAndCheck roda a cada 100ms até estabilizar),
    // que só existe se o efeito de troca de thread também estiver usando
    // scrollToIndex em vez de escrever scrollTop bruto.
    expect(scrollToIndexMock.mock.calls.length).toBeGreaterThan(5);
    expect(scrollToIndexMock).toHaveBeenLastCalledWith(79, { align: "end" });
  });
});

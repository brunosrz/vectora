// @vitest-environment jsdom
/**
 * Tests para MessageItem: render de mensagem do usuário e do assistente
 * (com strip do envelope markdown), e botão de copiar.
 */

import { describe, expect, it, afterEach, vi } from "vitest";
import {
  render as rtlRender,
  screen,
  cleanup,
  fireEvent,
} from "@testing-library/react";
import { TooltipProvider } from "@/components/ui/tooltip";
import { MessageItem } from "../message-item";
import type { Message } from "@/lib/types";

afterEach(cleanup);

function render(ui: React.ReactElement) {
  return rtlRender(<TooltipProvider>{ui}</TooltipProvider>);
}

type Props = Parameters<typeof MessageItem>[0];

function msg(over: Partial<Message>): Message {
  return {
    id: "m1",
    role: "assistant",
    content: "",
    timestamp: new Date(),
    ...over,
  } as unknown as Message;
}

function baseProps(message: Message, over: Partial<Props> = {}): Props {
  return {
    message,
    isLastAssistant: false,
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
    ...over,
  } as Props;
}

describe("MessageItem", () => {
  it("renderiza o conteúdo de uma mensagem do usuário", () => {
    render(
      <MessageItem
        {...baseProps(msg({ role: "user", content: "olá mundo" }))}
      />,
    );
    expect(screen.getByText("olá mundo")).toBeInTheDocument();
  });

  it("remove o envelope markdown do conteúdo do assistente", () => {
    render(
      <MessageItem
        {...baseProps(
          msg({
            role: "assistant",
            content: "``````markdown\nResposta limpa\n``````",
          }),
        )}
      />,
    );
    expect(screen.getByText("Resposta limpa")).toBeInTheDocument();
    expect(screen.queryByText(/``````/)).toBeNull();
  });

  it("copiar chama onCopy com o conteúdo e o id", () => {
    const onCopy = vi.fn();
    render(
      <MessageItem
        {...baseProps(msg({ id: "x9", role: "assistant", content: "texto" }), {
          onCopy,
        })}
      />,
    );
    const copyBtn = screen
      .getAllByRole("button")
      .find((b) => /copiar|copy/i.test(b.getAttribute("aria-label") ?? ""));
    expect(copyBtn).toBeTruthy();
    fireEvent.click(copyBtn!);
    expect(onCopy).toHaveBeenCalledWith("texto", "x9");
  });

  // Sprint 3b — botão copiar em mensagens do usuário
  it("mensagem do usuário tem botão copiar (3b)", () => {
    const onCopy = vi.fn();
    render(
      <MessageItem
        {...baseProps(
          msg({ id: "u1", role: "user", content: "minha pergunta" }),
          {
            onCopy,
          },
        )}
      />,
    );
    const copyBtn = screen
      .getAllByRole("button")
      .find((b) => /copiar|copy/i.test(b.getAttribute("aria-label") ?? ""));
    expect(copyBtn).toBeTruthy();
    fireEvent.click(copyBtn!);
    expect(onCopy).toHaveBeenCalledWith("minha pergunta", "u1");
  });

  // Sprint 3c — botões assistente usam h-6 w-6 (não h-7 w-7)
  it("botões do assistente usam h-6 w-6 (3c)", () => {
    const { container } = render(
      <MessageItem
        {...baseProps(
          msg({ id: "a2", role: "assistant", content: "resposta" }),
        )}
      />,
    );
    const buttons = container.querySelectorAll("button");
    const actionBtns = Array.from(buttons).filter(
      (b) => b.className.includes("h-6") && b.className.includes("w-6"),
    );
    expect(actionBtns.length).toBeGreaterThan(0);
    // Nenhum botão de ação deve usar h-7 w-7
    const oldSizeBtns = Array.from(buttons).filter(
      (b) => b.className.includes("h-7") && b.className.includes("w-7"),
    );
    expect(oldSizeBtns).toHaveLength(0);
  });

  // Sprint 3a — metadata (timestamp) fica na barra de botões, não na bolha de conteúdo
  it("metadata de duração está na barra justify-between, não na bolha de markdown (3a)", () => {
    const { container } = render(
      <MessageItem
        {...baseProps(
          msg({
            id: "a3",
            role: "assistant",
            content: "texto da resposta",
            isThinking: false,
            thinkingDuration: 3000,
          }),
        )}
      />,
    );
    expect(screen.getByText("texto da resposta")).toBeInTheDocument();
    // Barra de botões usa justify-between para posicionar botões + metadata
    const metaBar = container.querySelector("[class*='justify-between']");
    expect(metaBar).toBeTruthy();
    // Span de metadata está dentro da barra (classe tabular-nums)
    const metaSpan = metaBar?.querySelector("[class*='tabular-nums']");
    expect(metaSpan).toBeTruthy();
    expect(metaSpan?.textContent).toMatch(/3\.0s/);
  });
});

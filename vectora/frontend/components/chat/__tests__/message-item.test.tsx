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
});

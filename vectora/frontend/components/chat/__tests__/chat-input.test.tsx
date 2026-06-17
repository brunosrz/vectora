// @vitest-environment jsdom
/**
 * Tests para ChatInput: textarea controlado, botão de enviar (habilita só com
 * texto + usuário online) e callback onSend. Cobre o layout pós-swap
 * (enviar dentro da linha do input).
 */

import { describe, expect, it, afterEach, vi } from "vitest";
import {
  render as rtlRender,
  screen,
  cleanup,
  fireEvent,
} from "@testing-library/react";
import { TooltipProvider } from "@/components/ui/tooltip";
import { ChatInput } from "../chat-input";
import { m } from "@/lib/paraglide/messages";

afterEach(cleanup);

// ChatInput usa Tooltip — precisa do provider no entorno.
function render(ui: React.ReactElement) {
  return rtlRender(<TooltipProvider>{ui}</TooltipProvider>);
}

type Props = Parameters<typeof ChatInput>[0];

function baseProps(over: Partial<Props> = {}): Props {
  return {
    input: "",
    onInputChange: vi.fn(),
    onSend: vi.fn(),
    onKeyDown: vi.fn(),
    isLoading: false,
    isStopping: false,
    onStop: vi.fn(),
    userId: "u1",
    attachedFiles: [],
    uploadError: null,
    inputError: null,
    isDragging: false,
    onDragOver: vi.fn(),
    onDragLeave: vi.fn(),
    onDrop: vi.fn(),
    onPaste: vi.fn(),
    onRemoveFile: vi.fn(),
    onFileButtonClick: vi.fn(),
    fileInputRef: { current: null },
    onFileSelect: vi.fn(),
    ...over,
  } as Props;
}

function sendButton(): HTMLButtonElement {
  return screen.getByRole("button", {
    name: m.tooltip_chat_send(),
  }) as HTMLButtonElement;
}

describe("ChatInput", () => {
  it("renderiza o textarea de mensagem", () => {
    render(<ChatInput {...baseProps()} />);
    expect(screen.getByRole("textbox")).toBeInTheDocument();
  });

  it("desabilita o enviar quando o input está vazio", () => {
    render(<ChatInput {...baseProps({ input: "" })} />);
    expect(sendButton()).toBeDisabled();
  });

  it("habilita o enviar quando há texto", () => {
    render(<ChatInput {...baseProps({ input: "olá" })} />);
    expect(sendButton()).not.toBeDisabled();
  });

  it("clicar em enviar chama onSend", () => {
    const onSend = vi.fn();
    render(<ChatInput {...baseProps({ input: "oi", onSend })} />);
    fireEvent.click(sendButton());
    expect(onSend).toHaveBeenCalledTimes(1);
  });

  it("digitar no textarea chama onInputChange", () => {
    const onInputChange = vi.fn();
    render(<ChatInput {...baseProps({ onInputChange })} />);
    fireEvent.change(screen.getByRole("textbox"), {
      target: { value: "novo" },
    });
    expect(onInputChange).toHaveBeenCalledWith("novo");
  });
});

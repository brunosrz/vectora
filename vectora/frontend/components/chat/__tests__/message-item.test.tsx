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

  // ── Layout WhatsApp ────────────────────────────────────────────────────────

  it("mensagem do usuário tem container com justify-end (alinhamento direita)", () => {
    const { container } = render(
      <MessageItem {...baseProps(msg({ role: "user", content: "olá" }))} />,
    );
    const outer = container.querySelector(".justify-end");
    expect(outer).toBeTruthy();
  });

  it("mensagem do assistente NÃO tem justify-end", () => {
    const { container } = render(
      <MessageItem
        {...baseProps(msg({ role: "assistant", content: "resposta" }))}
      />,
    );
    expect(container.querySelector(".justify-end")).toBeNull();
  });

  it("bolha do usuário usa bg-user-bubble e não bg-muted", () => {
    const { container } = render(
      <MessageItem {...baseProps(msg({ role: "user", content: "olá" }))} />,
    );
    const bubble = container.querySelector(".bg-user-bubble");
    expect(bubble).toBeTruthy();
    // Não deve ter a classe de fundo do assistente
    expect(bubble?.className).not.toContain("bg-muted");
  });

  it("bolha do assistente usa bg-muted e não bg-user-bubble", () => {
    const { container } = render(
      <MessageItem
        {...baseProps(msg({ role: "assistant", content: "resposta" }))}
      />,
    );
    const bubble = container.querySelector(".bg-muted");
    expect(bubble).toBeTruthy();
    expect(container.querySelector(".bg-user-bubble")).toBeNull();
  });

  it("avatar (imagem) está presente para mensagem do assistente", () => {
    const { container } = render(
      <MessageItem
        {...baseProps(msg({ role: "assistant", content: "resposta" }))}
      />,
    );
    const img = container.querySelector("img");
    expect(img).toBeTruthy();
    expect(img?.getAttribute("alt")).toMatch(/assistant/i);
  });

  it("avatar está AUSENTE para mensagem do usuário", () => {
    const { container } = render(
      <MessageItem
        {...baseProps(msg({ role: "user", content: "pergunta" }))}
      />,
    );
    // O único img seria o avatar — não deve haver nenhum img com alt de assistente
    const assistantImg = Array.from(container.querySelectorAll("img")).find(
      (i) => /assistant/i.test(i.getAttribute("alt") ?? ""),
    );
    expect(assistantImg).toBeUndefined();
  });

  it("bolha do usuário tem max-w-[85%] para limitar largura", () => {
    const { container } = render(
      <MessageItem
        {...baseProps(
          msg({ role: "user", content: "mensagem longa ".repeat(20) }),
        )}
      />,
    );
    // O wrapper interno da bolha do usuário deve ter max-w-[85%]
    const wrapper = container.querySelector(".max-w-\\[85\\%\\]");
    expect(wrapper).toBeTruthy();
  });

  it("bolha do assistente usa flex-1 (não max-w-[85%])", () => {
    const { container } = render(
      <MessageItem
        {...baseProps(msg({ role: "assistant", content: "resposta" }))}
      />,
    );
    expect(container.querySelector(".flex-1")).toBeTruthy();
    expect(container.querySelector(".max-w-\\[85\\%\\]")).toBeNull();
  });

  // ── D2 — Bloco de progresso do agente ─────────────────────────────────────

  it("bloco <details> aparece quando isThinking=true (streaming ativo)", () => {
    const { container } = render(
      <MessageItem
        {...baseProps(
          msg({
            role: "assistant",
            content: "",
            isThinking: true,
            thinkingStartTime: Date.now(),
          }),
        )}
      />,
    );
    expect(container.querySelector("details")).toBeTruthy();
  });

  it("bloco <details> aparece quando há thinkingSteps (pós-stream)", () => {
    const { container } = render(
      <MessageItem
        {...baseProps(
          msg({
            role: "assistant",
            content: "resposta",
            isThinking: false,
            thinkingSteps: ["Passo 1", "Passo 2"],
          }),
        )}
      />,
    );
    expect(container.querySelector("details")).toBeTruthy();
    // Os passos devem aparecer no conteúdo
    expect(screen.getByText("Passo 1")).toBeInTheDocument();
    expect(screen.getByText("Passo 2")).toBeInTheDocument();
  });

  it("bloco <details> NÃO aparece com thinkingStartTime setado mas isThinking=false e sem steps (bug fix)", () => {
    // Bug anterior: || message.thinkingStartTime era sempre truthy → retângulo preto vazio
    const { container } = render(
      <MessageItem
        {...baseProps(
          msg({
            role: "assistant",
            content: "resposta",
            isThinking: false,
            thinkingStartTime: Date.now() - 5000,
            thinkingSteps: [],
          }),
        )}
      />,
    );
    expect(container.querySelector("details")).toBeNull();
  });

  it("bloco <details> NÃO aparece quando não há dados de thinking", () => {
    const { container } = render(
      <MessageItem
        {...baseProps(
          msg({
            role: "assistant",
            content: "resposta simples",
            isThinking: false,
          }),
        )}
      />,
    );
    expect(container.querySelector("details")).toBeNull();
  });

  it("bloco <details> NÃO aparece para mensagem do usuário mesmo com thinkingSteps", () => {
    // Guard: usuário nunca exibe bloco de thinking
    const { container } = render(
      <MessageItem
        {...baseProps(
          msg({
            role: "user",
            content: "pergunta",
            isThinking: true,
            thinkingSteps: ["Passo X"],
          } as unknown as Message),
        )}
      />,
    );
    expect(container.querySelector("details")).toBeNull();
  });

  it("thinkingSteps vazio (length=0) não exibe bloco <details>", () => {
    const { container } = render(
      <MessageItem
        {...baseProps(
          msg({
            role: "assistant",
            content: "resposta",
            isThinking: false,
            thinkingSteps: [],
          }),
        )}
      />,
    );
    expect(container.querySelector("details")).toBeNull();
  });

  // ── Casos limite de conteúdo ───────────────────────────────────────────────

  it("conteúdo vazio não quebra a renderização", () => {
    expect(() =>
      render(
        <MessageItem {...baseProps(msg({ role: "assistant", content: "" }))} />,
      ),
    ).not.toThrow();
  });

  it("conteúdo muito longo renderiza sem erro", () => {
    const longContent = "palavra ".repeat(500);
    expect(() =>
      render(
        <MessageItem
          {...baseProps(msg({ role: "user", content: longContent }))}
        />,
      ),
    ).not.toThrow();
    expect(screen.getByText(longContent.trim())).toBeInTheDocument();
  });

  it("remove o envelope mesmo com conteúdo markdown extenso", () => {
    const body =
      "# Título\n\n- item 1\n- item 2\n\n```python\nprint('hi')\n```";
    render(
      <MessageItem
        {...baseProps(
          msg({
            role: "assistant",
            content: `\`\`\`\`\`\`markdown\n${body}\n\`\`\`\`\`\``,
          }),
        )}
      />,
    );
    expect(screen.getByText("Título")).toBeInTheDocument();
    expect(screen.queryByText(/``````/)).toBeNull();
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

  it("clicar na thumbnail de imagem abre o lightbox em tela cheia", () => {
    render(
      <MessageItem
        {...baseProps(
          msg({
            role: "user",
            content: "olha essa imagem",
            images: [
              {
                id: "img1",
                name: "foto.png",
                mimeType: "image/png",
                base64: "AAAA",
                size: 1234,
              },
            ],
          }),
        )}
      />,
    );

    fireEvent.click(screen.getByAltText("foto.png"));

    // Lightbox mostra a mesma imagem em um <img> adicional (dialog)
    expect(screen.getAllByAltText("foto.png")).toHaveLength(2);
  });

  it("fechar o lightbox some com a segunda instância da imagem (edge)", () => {
    render(
      <MessageItem
        {...baseProps(
          msg({
            role: "user",
            content: "olha essa imagem",
            images: [
              {
                id: "img1",
                name: "foto.png",
                mimeType: "image/png",
                base64: "AAAA",
                size: 1234,
              },
            ],
          }),
        )}
      />,
    );

    fireEvent.click(screen.getByAltText("foto.png"));
    expect(screen.getAllByAltText("foto.png")).toHaveLength(2);

    fireEvent.click(screen.getByTitle("Cancel"));
    expect(screen.getAllByAltText("foto.png")).toHaveLength(1);
  });
});

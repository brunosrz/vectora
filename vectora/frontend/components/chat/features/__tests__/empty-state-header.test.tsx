// @vitest-environment jsdom
import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, cleanup, fireEvent } from "@testing-library/react";

vi.mock("@/lib/paraglide/messages", () => ({
  m: {
    welcome_title: () => "O que posso fazer por você?",
    welcome_start_chat: () => "Chat",
    welcome_start_chat_desc: () => "Conversa livre, sem projeto",
    welcome_start_code: () => "Sessão de código",
    welcome_start_code_desc: () => "Com pasta de projeto e ferramentas",
    welcome_suggestion_1: () => "Sugestão 1",
    welcome_suggestion_2: () => "Sugestão 2",
    welcome_suggestion_3: () => "Sugestão 3",
  },
}));

vi.mock("@/lib/i18n-dyn", () => ({
  mDyn: (key: string) => key,
}));

vi.mock("@tanstack/react-query", () => ({
  useQuery: () => ({ data: undefined }),
}));

vi.mock("@/lib/api/vectora-client", () => ({
  getStackHint: vi.fn(),
}));

vi.mock("next/image", () => ({
  default: ({ alt, ...rest }: { alt: string } & Record<string, unknown>) => (
    // eslint-disable-next-line @next/next/no-img-element
    <img alt={alt} {...(rest as React.ImgHTMLAttributes<HTMLImageElement>)} />
  ),
}));

import { EmptyStateHeader } from "../empty-state-header";

afterEach(cleanup);

describe("EmptyStateHeader", () => {
  it("renderiza o título de boas-vindas", () => {
    render(<EmptyStateHeader />);
    expect(screen.getByText("O que posso fazer por você?")).toBeInTheDocument();
  });

  it("não exibe CTAs de modo quando sem handlers (estado padrão de chat em andamento)", () => {
    render(<EmptyStateHeader />);
    expect(screen.queryByText("Chat")).toBeNull();
    expect(screen.queryByText("Sessão de código")).toBeNull();
  });

  it("exibe botão Chat quando onStartChat é fornecido", () => {
    render(<EmptyStateHeader onStartChat={vi.fn()} />);
    expect(screen.getByText("Chat")).toBeInTheDocument();
    expect(screen.getByText("Conversa livre, sem projeto")).toBeInTheDocument();
  });

  it("exibe botão Sessão de código quando onStartCode é fornecido", () => {
    render(<EmptyStateHeader onStartCode={vi.fn()} />);
    expect(screen.getByText("Sessão de código")).toBeInTheDocument();
    expect(
      screen.getByText("Com pasta de projeto e ferramentas"),
    ).toBeInTheDocument();
  });

  it("exibe ambos os botões quando os dois handlers são fornecidos (home screen)", () => {
    render(<EmptyStateHeader onStartChat={vi.fn()} onStartCode={vi.fn()} />);
    expect(screen.getByText("Chat")).toBeInTheDocument();
    expect(screen.getByText("Sessão de código")).toBeInTheDocument();
  });

  it("clicar em Chat chama onStartChat", () => {
    const onStartChat = vi.fn();
    render(
      <EmptyStateHeader onStartChat={onStartChat} onStartCode={vi.fn()} />,
    );
    fireEvent.click(screen.getByText("Chat").closest("button")!);
    expect(onStartChat).toHaveBeenCalledOnce();
  });

  it("clicar em Sessão de código chama onStartCode", () => {
    const onStartCode = vi.fn();
    render(
      <EmptyStateHeader onStartChat={vi.fn()} onStartCode={onStartCode} />,
    );
    fireEvent.click(screen.getByText("Sessão de código").closest("button")!);
    expect(onStartCode).toHaveBeenCalledOnce();
  });

  it("não renderiza sugestões quando onSelect não é fornecido", () => {
    render(<EmptyStateHeader onStartChat={vi.fn()} onStartCode={vi.fn()} />);
    // mDyn retorna a chave; sugestões renderizam como "stack.unknown.1" etc.
    expect(screen.queryByText("stack.unknown.1")).toBeNull();
  });

  it("renderiza sugestões quando onSelect é fornecido e chama ao clicar", () => {
    const onSelect = vi.fn();
    render(
      <EmptyStateHeader
        onSelect={onSelect}
        onStartChat={vi.fn()}
        onStartCode={vi.fn()}
      />,
    );
    const chip = screen.getByText("stack.unknown.1");
    fireEvent.click(chip);
    expect(onSelect).toHaveBeenCalledWith("stack.unknown.1");
  });

  it("edge: apenas onStartChat — sem botão Sessão de código", () => {
    render(<EmptyStateHeader onStartChat={vi.fn()} />);
    expect(screen.queryByText("Sessão de código")).toBeNull();
  });

  it("edge: apenas onStartCode — sem botão Chat", () => {
    render(<EmptyStateHeader onStartCode={vi.fn()} />);
    expect(screen.queryByText("Chat")).toBeNull();
  });

  it("edge: handlers undefined explícito — sem CTAs", () => {
    render(
      <EmptyStateHeader onStartChat={undefined} onStartCode={undefined} />,
    );
    expect(screen.queryByText("Chat")).toBeNull();
    expect(screen.queryByText("Sessão de código")).toBeNull();
  });
});

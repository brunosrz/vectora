// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";

import TokenReveal from "./TokenReveal";

vi.mock("#/paraglide/messages", () => ({
  m: new Proxy(
    {},
    {
      get:
        (_t, prop) =>
        (..._args: unknown[]) =>
          String(prop),
    },
  ),
}));

const { mockGetToken, mockRotateToken, mockToastSuccess, mockToastError } =
  vi.hoisted(() => ({
    mockGetToken: vi.fn(),
    mockRotateToken: vi.fn(),
    mockToastSuccess: vi.fn(),
    mockToastError: vi.fn(),
  }));

vi.mock("#/server/fns/token", () => ({
  getToken: mockGetToken,
  rotateToken: mockRotateToken,
}));

vi.mock("sonner", () => ({
  toast: { success: mockToastSuccess, error: mockToastError },
}));

function renderWithClient(ui: ReactNode) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

beforeEach(() => {
  vi.clearAllMocks();
  Object.assign(navigator, { clipboard: { writeText: vi.fn() } });
});

describe("TokenReveal", () => {
  it("mostra o botão de revelar no estado inicial", () => {
    renderWithClient(<TokenReveal initialRevealed={false} />);
    expect(screen.getByText("token_reveal_cta")).toBeInTheDocument();
  });

  it("mostra o token em texto plano na primeira revelação", async () => {
    mockGetToken.mockResolvedValue({ revealed: false, token: "vct_abc123" });
    renderWithClient(<TokenReveal initialRevealed={false} />);

    fireEvent.click(screen.getByText("token_reveal_cta"));

    await waitFor(() =>
      expect(screen.getByText("vct_abc123")).toBeInTheDocument(),
    );
    expect(screen.getByText("token_show_once_warning")).toBeInTheDocument();
  });

  it("mostra aviso de 'já revelado' + botão de rotacionar quando revealed=true (edge)", async () => {
    mockGetToken.mockResolvedValue({ revealed: true, token: null });
    renderWithClient(<TokenReveal initialRevealed={false} />);

    fireEvent.click(screen.getByText("token_reveal_cta"));

    await waitFor(() =>
      expect(screen.getByText("token_already_revealed")).toBeInTheDocument(),
    );
    expect(screen.getByText("token_rotate_cta")).toBeInTheDocument();
  });

  it("já parte do estado 'revelado' quando initialRevealed=true", () => {
    renderWithClient(<TokenReveal initialRevealed={true} />);
    expect(screen.getByText("token_already_revealed")).toBeInTheDocument();
  });

  it("copiar limpa o token da tela e mostra toast de sucesso", async () => {
    mockGetToken.mockResolvedValue({ revealed: false, token: "vct_copyme" });
    renderWithClient(<TokenReveal initialRevealed={false} />);
    fireEvent.click(screen.getByText("token_reveal_cta"));
    await waitFor(() =>
      expect(screen.getByText("vct_copyme")).toBeInTheDocument(),
    );

    fireEvent.click(screen.getByTitle("token_copy_cta"));

    expect(navigator.clipboard.writeText).toHaveBeenCalledWith("vct_copyme");
    expect(mockToastSuccess).toHaveBeenCalledWith("token_copied");
    // token some da tela; como revealed continua false, volta ao CTA de revelar.
    await waitFor(() =>
      expect(screen.getByText("token_reveal_cta")).toBeInTheDocument(),
    );
  });

  it("rotacionar exibe o novo token e o toast de confirmação", async () => {
    mockGetToken.mockResolvedValue({ revealed: true, token: null });
    mockRotateToken.mockResolvedValue({ token: "vct_rotated999" });
    renderWithClient(<TokenReveal initialRevealed={false} />);
    fireEvent.click(screen.getByText("token_reveal_cta"));
    await waitFor(() => screen.getByText("token_rotate_cta"));

    fireEvent.click(screen.getByText("token_rotate_cta"));

    await waitFor(() =>
      expect(screen.getByText("vct_rotated999")).toBeInTheDocument(),
    );
    expect(mockToastSuccess).toHaveBeenCalledWith("token_rotated");
  });

  it("mostra toast de erro quando a revelação falha (edge)", async () => {
    mockGetToken.mockRejectedValue(new Error("services_error_500"));
    renderWithClient(<TokenReveal initialRevealed={false} />);

    fireEvent.click(screen.getByText("token_reveal_cta"));

    await waitFor(() =>
      expect(mockToastError).toHaveBeenCalledWith("error_generic"),
    );
  });

  it("mostra o guia de início rápido só quando welcome=true", () => {
    renderWithClient(<TokenReveal initialRevealed={false} welcome />);
    expect(screen.getByText("token_quickstart_heading")).toBeInTheDocument();
  });

  it("não mostra o guia de início rápido por padrão (edge)", () => {
    renderWithClient(<TokenReveal initialRevealed={false} />);
    expect(
      screen.queryByText("token_quickstart_heading"),
    ).not.toBeInTheDocument();
  });
});

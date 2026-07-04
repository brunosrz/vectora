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
  it("mostra o botão de revelar quando o token está disponível", () => {
    renderWithClient(<TokenReveal initialAvailable={true} />);
    expect(screen.getByText("token_reveal_cta")).toBeInTheDocument();
  });

  it("mostra o token em texto plano ao revelar", async () => {
    mockGetToken.mockResolvedValue({ token: "vct_abc123" });
    renderWithClient(<TokenReveal initialAvailable={true} />);

    fireEvent.click(screen.getByText("token_reveal_cta"));

    await waitFor(() =>
      expect(screen.getByText("vct_abc123")).toBeInTheDocument(),
    );
    expect(screen.getByText("token_keep_secret_warning")).toBeInTheDocument();
    // recuperável — o botão de rotacionar fica disponível junto do token,
    // não é a única saída de um estado "sem volta".
    expect(screen.getByText("token_rotate_cta")).toBeInTheDocument();
  });

  it("mostra aviso de token indisponível (conta legada) + CTA de rotacionar quando initialAvailable=false (edge)", () => {
    renderWithClient(<TokenReveal initialAvailable={false} />);
    expect(screen.getByText("token_not_available")).toBeInTheDocument();
    expect(screen.getByText("token_rotate_cta")).toBeInTheDocument();
    expect(screen.queryByText("token_reveal_cta")).not.toBeInTheDocument();
  });

  it("copiar mantém o token visível (recuperável, não é show-once) e mostra toast de sucesso", async () => {
    mockGetToken.mockResolvedValue({ token: "vct_copyme" });
    renderWithClient(<TokenReveal initialAvailable={true} />);
    fireEvent.click(screen.getByText("token_reveal_cta"));
    await waitFor(() =>
      expect(screen.getByText("vct_copyme")).toBeInTheDocument(),
    );

    fireEvent.click(screen.getByTitle("token_copy_cta"));

    expect(navigator.clipboard.writeText).toHaveBeenCalledWith("vct_copyme");
    expect(mockToastSuccess).toHaveBeenCalledWith("token_copied");
    expect(screen.getByText("vct_copyme")).toBeInTheDocument();
  });

  it("rotacionar a partir do token já revelado exibe o novo token e o toast de confirmação", async () => {
    mockGetToken.mockResolvedValue({ token: "vct_old" });
    mockRotateToken.mockResolvedValue({ token: "vct_rotated999" });
    renderWithClient(<TokenReveal initialAvailable={true} />);
    fireEvent.click(screen.getByText("token_reveal_cta"));
    await waitFor(() => screen.getByText("vct_old"));

    fireEvent.click(screen.getByText("token_rotate_cta"));

    await waitFor(() =>
      expect(screen.getByText("vct_rotated999")).toBeInTheDocument(),
    );
    expect(mockToastSuccess).toHaveBeenCalledWith("token_rotated");
  });

  it("rotacionar a partir do estado sem token (edge) passa a disponibilizar o token gerado", async () => {
    mockRotateToken.mockResolvedValue({ token: "vct_first" });
    renderWithClient(<TokenReveal initialAvailable={false} />);

    fireEvent.click(screen.getByText("token_rotate_cta"));

    await waitFor(() =>
      expect(screen.getByText("vct_first")).toBeInTheDocument(),
    );
  });

  it("mostra toast de erro quando a revelação falha (edge)", async () => {
    mockGetToken.mockRejectedValue(new Error("services_error_500"));
    renderWithClient(<TokenReveal initialAvailable={true} />);

    fireEvent.click(screen.getByText("token_reveal_cta"));

    await waitFor(() =>
      expect(mockToastError).toHaveBeenCalledWith("error_generic"),
    );
  });

  it("mostra o guia de início rápido só quando welcome=true", () => {
    renderWithClient(<TokenReveal initialAvailable={true} welcome />);
    expect(screen.getByText("token_quickstart_heading")).toBeInTheDocument();
  });

  it("não mostra o guia de início rápido por padrão (edge)", () => {
    renderWithClient(<TokenReveal initialAvailable={true} />);
    expect(
      screen.queryByText("token_quickstart_heading"),
    ).not.toBeInTheDocument();
  });
});

// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import type { SessionUser } from "#/server/fns/auth";

import AccountSection from "./AccountSection";

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

const { mockNavigate } = vi.hoisted(() => ({ mockNavigate: vi.fn() }));
vi.mock("@tanstack/react-router", () => ({ useNavigate: () => mockNavigate }));

const {
  mockUpdateProfile,
  mockSendMagicLink,
  mockExportData,
  mockRequestAccountDeletion,
  mockToastSuccess,
  mockToastError,
} = vi.hoisted(() => ({
  mockUpdateProfile: vi.fn(),
  mockSendMagicLink: vi.fn(),
  mockExportData: vi.fn(),
  mockRequestAccountDeletion: vi.fn(),
  mockToastSuccess: vi.fn(),
  mockToastError: vi.fn(),
}));

vi.mock("#/server/fns/profile", () => ({ updateProfile: mockUpdateProfile }));
vi.mock("#/server/fns/auth", () => ({ sendMagicLink: mockSendMagicLink }));
vi.mock("#/server/fns/gdpr", () => ({
  exportData: mockExportData,
  requestAccountDeletion: mockRequestAccountDeletion,
}));
vi.mock("sonner", () => ({
  toast: { success: mockToastSuccess, error: mockToastError },
}));

const USER: SessionUser = {
  id: "u1",
  email: "ana@example.com",
  full_name: "Ana Silva",
  country: "BR",
  language: "pt",
  email_verified: true,
  role: "user",
};

function renderWithClient(ui: ReactNode) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("AccountSection", () => {
  it("preenche os campos a partir do usuário", () => {
    renderWithClient(<AccountSection user={USER} />);
    expect(screen.getByDisplayValue("Ana Silva")).toBeInTheDocument();
    expect(screen.getByText("ana@example.com")).toBeInTheDocument();
  });

  it("desabilita salvar quando o nome tem menos de 2 caracteres (edge)", () => {
    renderWithClient(<AccountSection user={USER} />);
    const input = screen.getByDisplayValue("Ana Silva");

    fireEvent.change(input, { target: { value: "A" } });

    expect(screen.getByText("form_save")).toBeDisabled();
  });

  it("salva o perfil e mostra toast de sucesso", async () => {
    mockUpdateProfile.mockResolvedValue({ ok: true });
    renderWithClient(<AccountSection user={USER} />);

    fireEvent.click(screen.getByText("form_save"));

    await waitFor(() =>
      expect(mockToastSuccess).toHaveBeenCalledWith("account_profile_saved"),
    );
    expect(mockUpdateProfile).toHaveBeenCalledWith({
      data: { full_name: "Ana Silva", country: "BR", language: "pt" },
    });
  });

  it("mostra toast de erro quando salvar falha (edge)", async () => {
    mockUpdateProfile.mockRejectedValue(new Error("services_error_500"));
    renderWithClient(<AccountSection user={USER} />);

    fireEvent.click(screen.getByText("form_save"));

    await waitFor(() =>
      expect(mockToastError).toHaveBeenCalledWith("error_generic"),
    );
  });

  it("dispara magic link com o email do usuário", async () => {
    mockSendMagicLink.mockResolvedValue({ ok: true });
    renderWithClient(<AccountSection user={USER} />);

    fireEvent.click(screen.getByText("account_change_password"));

    await waitFor(() =>
      expect(mockSendMagicLink).toHaveBeenCalledWith({
        data: { email: "ana@example.com" },
      }),
    );
  });

  it("exportar dados cria um link de download com a URL retornada", async () => {
    mockExportData.mockResolvedValue({ url: "https://r2.test/export.json" });
    const clickSpy = vi
      .spyOn(HTMLAnchorElement.prototype, "click")
      .mockImplementation(() => {});
    renderWithClient(<AccountSection user={USER} />);

    fireEvent.click(screen.getByText("account_export_cta"));

    await waitFor(() => expect(clickSpy).toHaveBeenCalled());
    clickSpy.mockRestore();
  });

  it("botão de deletar conta exige digitar o email antes de habilitar (edge)", async () => {
    renderWithClient(<AccountSection user={USER} />);

    fireEvent.click(screen.getByText("account_delete_cta"));
    const confirmBtn = screen.getByText("account_delete_confirm_cta");
    expect(confirmBtn).toBeDisabled();

    fireEvent.change(screen.getByPlaceholderText("ana@example.com"), {
      target: { value: "email-errado@x.com" },
    });
    expect(confirmBtn).toBeDisabled();

    fireEvent.change(screen.getByPlaceholderText("ana@example.com"), {
      target: { value: "ana@example.com" },
    });
    expect(confirmBtn).not.toBeDisabled();
  });

  it("cancelar a exclusão volta ao estado inicial e limpa o campo (edge)", () => {
    renderWithClient(<AccountSection user={USER} />);
    fireEvent.click(screen.getByText("account_delete_cta"));

    fireEvent.click(screen.getByText("form_cancel"));

    expect(screen.getByText("account_delete_cta")).toBeInTheDocument();
    expect(
      screen.queryByPlaceholderText("ana@example.com"),
    ).not.toBeInTheDocument();
  });

  it("confirmar a exclusão navega para a home após sucesso", async () => {
    mockRequestAccountDeletion.mockResolvedValue({ ok: true });
    renderWithClient(<AccountSection user={USER} />);
    fireEvent.click(screen.getByText("account_delete_cta"));
    fireEvent.change(screen.getByPlaceholderText("ana@example.com"), {
      target: { value: "ana@example.com" },
    });

    fireEvent.click(screen.getByText("account_delete_confirm_cta"));

    await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith({ to: "/" }));
  });
});

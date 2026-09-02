// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import type * as GhBotModule from "#/server/fns/gh-bot";

import GhBotSection from "./GhBotSection";

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

const {
  mockGetGhBotSettings,
  mockSaveGhBotSettings,
  mockListGhBotTokens,
  mockCreateGhBotToken,
  mockRevokeGhBotToken,
  mockToastError,
  mockToastSuccess,
} = vi.hoisted(() => ({
  mockGetGhBotSettings: vi.fn(),
  mockSaveGhBotSettings: vi.fn(),
  mockListGhBotTokens: vi.fn(),
  mockCreateGhBotToken: vi.fn(),
  mockRevokeGhBotToken: vi.fn(),
  mockToastError: vi.fn(),
  mockToastSuccess: vi.fn(),
}));

vi.mock("#/server/fns/gh-bot", async () => {
  const actual = await vi.importActual<typeof GhBotModule>(
    "#/server/fns/gh-bot",
  );
  return {
    ...actual,
    getGhBotSettings: mockGetGhBotSettings,
    saveGhBotSettings: mockSaveGhBotSettings,
    listGhBotTokens: mockListGhBotTokens,
    createGhBotToken: mockCreateGhBotToken,
    revokeGhBotToken: mockRevokeGhBotToken,
  };
});

vi.mock("sonner", () => ({
  toast: { error: mockToastError, success: mockToastSuccess },
}));

function renderWithClient(ui: ReactNode) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

beforeEach(() => {
  vi.clearAllMocks();
  mockListGhBotTokens.mockResolvedValue([]);
  Object.assign(navigator, { clipboard: { writeText: vi.fn() } });
});

describe("GhBotSection", () => {
  it("mostra o skeleton enquanto carrega e depois o formulário sem settings salvas", async () => {
    mockGetGhBotSettings.mockResolvedValue(null);
    const { container } = renderWithClient(<GhBotSection />);

    expect(container.querySelector(".animate-pulse")).toBeInTheDocument();

    await waitFor(() =>
      expect(screen.getByText("gh_bot_settings_title")).toBeInTheDocument(),
    );
  });

  it("pré-preenche provider/modelo/estilo quando já existem settings salvas", async () => {
    mockGetGhBotSettings.mockResolvedValue({
      provider: "openai",
      model: "gpt-5",
      review_style: "strict",
      updated_at: "2026-01-01 00:00:00",
    });
    renderWithClient(<GhBotSection />);

    await waitFor(() =>
      expect(screen.getByDisplayValue("gpt-5")).toBeInTheDocument(),
    );
    expect(screen.getByDisplayValue("OpenAI")).toBeInTheDocument();
  });

  it("erro/borda: salvar sem modelo mostra o erro e não chama o servidor", async () => {
    mockGetGhBotSettings.mockResolvedValue(null);
    renderWithClient(<GhBotSection />);
    await waitFor(() => screen.getByText("gh_bot_save_button"));

    fireEvent.click(screen.getByText("gh_bot_save_button"));

    expect(
      await screen.findByText("gh_bot_error_missing_model"),
    ).toBeInTheDocument();
    expect(mockSaveGhBotSettings).not.toHaveBeenCalled();
  });

  it("erro/borda: salvar com modelo mas sem chave mostra o erro e não chama o servidor", async () => {
    mockGetGhBotSettings.mockResolvedValue(null);
    renderWithClient(<GhBotSection />);
    await waitFor(() => screen.getByText("gh_bot_save_button"));

    fireEvent.change(screen.getByPlaceholderText("gh_bot_model_placeholder"), {
      target: { value: "claude-sonnet-5" },
    });
    fireEvent.click(screen.getByText("gh_bot_save_button"));

    expect(
      await screen.findByText("gh_bot_error_missing_key"),
    ).toBeInTheDocument();
    expect(mockSaveGhBotSettings).not.toHaveBeenCalled();
  });

  it("salva com sucesso, limpa o campo de chave e mostra toast", async () => {
    mockGetGhBotSettings.mockResolvedValue(null);
    mockSaveGhBotSettings.mockResolvedValue({ ok: true });
    renderWithClient(<GhBotSection />);
    await waitFor(() => screen.getByText("gh_bot_save_button"));

    fireEvent.change(screen.getByPlaceholderText("gh_bot_model_placeholder"), {
      target: { value: "claude-sonnet-5" },
    });
    fireEvent.change(
      screen.getByPlaceholderText("gh_bot_api_key_placeholder"),
      { target: { value: "sk-ant-abc" } },
    );
    fireEvent.click(screen.getByText("gh_bot_save_button"));

    await waitFor(() =>
      expect(mockSaveGhBotSettings).toHaveBeenCalledWith({
        data: {
          provider: "anthropic",
          model: "claude-sonnet-5",
          providerApiKey: "sk-ant-abc",
          reviewStyle: "balanced",
        },
      }),
    );
    await waitFor(() =>
      expect(mockToastSuccess).toHaveBeenCalledWith("gh_bot_saved"),
    );
    expect(
      (
        screen.getByPlaceholderText(
          "gh_bot_api_key_placeholder",
        ) as HTMLInputElement
      ).value,
    ).toBe("");
  });

  it("erro/borda: falha ao salvar mostra toast de erro", async () => {
    mockGetGhBotSettings.mockResolvedValue(null);
    mockSaveGhBotSettings.mockRejectedValue(new Error("services_error_500"));
    renderWithClient(<GhBotSection />);
    await waitFor(() => screen.getByText("gh_bot_save_button"));

    fireEvent.change(screen.getByPlaceholderText("gh_bot_model_placeholder"), {
      target: { value: "claude-sonnet-5" },
    });
    fireEvent.change(
      screen.getByPlaceholderText("gh_bot_api_key_placeholder"),
      { target: { value: "sk-ant-abc" } },
    );
    fireEvent.click(screen.getByText("gh_bot_save_button"));

    await waitFor(() =>
      expect(mockToastError).toHaveBeenCalledWith("error_generic"),
    );
  });

  it("lista vazia mostra a mensagem de nenhum token ainda", async () => {
    mockGetGhBotSettings.mockResolvedValue(null);
    mockListGhBotTokens.mockResolvedValue([]);
    renderWithClient(<GhBotSection />);

    await waitFor(() =>
      expect(screen.getByText("gh_bot_no_tokens")).toBeInTheDocument(),
    );
  });

  it("gera um token novo, mostra o segredo uma vez e recarrega a lista", async () => {
    mockGetGhBotSettings.mockResolvedValue(null);
    mockListGhBotTokens.mockResolvedValue([]);
    mockCreateGhBotToken.mockResolvedValue({ secret: "vbt_abc123" });
    renderWithClient(<GhBotSection />);
    await waitFor(() => screen.getByText("gh_bot_new_token_button"));

    fireEvent.click(screen.getByText("gh_bot_new_token_button"));

    await waitFor(() =>
      expect(screen.getByText(/vbt_abc123/)).toBeInTheDocument(),
    );
    expect(mockListGhBotTokens).toHaveBeenCalledTimes(2);
  });

  it("lista um token ativo e revoga com sucesso", async () => {
    mockGetGhBotSettings.mockResolvedValue(null);
    mockListGhBotTokens.mockResolvedValue([
      {
        id: "11111111-2222-3333-4444-555555555555",
        repo_scope: null,
        created_at: "2026-01-01 00:00:00",
        revoked_at: null,
      },
    ]);
    mockRevokeGhBotToken.mockResolvedValue({ ok: true });
    renderWithClient(<GhBotSection />);
    await waitFor(() =>
      expect(screen.getByText("gh_bot_status_active")).toBeInTheDocument(),
    );

    fireEvent.click(screen.getByText("gh_bot_revoke_button"));

    await waitFor(() =>
      expect(mockRevokeGhBotToken).toHaveBeenCalledWith({
        data: { id: "11111111-2222-3333-4444-555555555555" },
      }),
    );
  });

  it("botão de copiar o YAML de instalação copia o conteúdo pro clipboard e mostra toast", async () => {
    mockGetGhBotSettings.mockResolvedValue(null);
    renderWithClient(<GhBotSection />);
    await waitFor(() => screen.getByText("gh_bot_install_title"));

    fireEvent.click(screen.getByTitle("gh_bot_yaml_copy_cta"));

    await waitFor(() =>
      expect(navigator.clipboard.writeText).toHaveBeenCalledTimes(1),
    );
    const copied = (navigator.clipboard.writeText as ReturnType<typeof vi.fn>)
      .mock.calls[0][0] as string;
    expect(copied).toContain("vectora-ltda/vectora-review-action@v1");
    await waitFor(() =>
      expect(mockToastSuccess).toHaveBeenCalledWith("gh_bot_yaml_copied"),
    );
  });

  it("erro/borda: falha ao copiar o YAML (clipboard rejeitado) mostra toast de erro, não de sucesso", async () => {
    mockGetGhBotSettings.mockResolvedValue(null);
    Object.assign(navigator, {
      clipboard: { writeText: vi.fn().mockRejectedValue(new Error("denied")) },
    });
    renderWithClient(<GhBotSection />);
    await waitFor(() => screen.getByText("gh_bot_install_title"));

    fireEvent.click(screen.getByTitle("gh_bot_yaml_copy_cta"));

    await waitFor(() =>
      expect(mockToastError).toHaveBeenCalledWith("error_generic"),
    );
    expect(mockToastSuccess).not.toHaveBeenCalledWith("gh_bot_yaml_copied");
  });
});

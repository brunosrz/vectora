// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";

import ApiKeysList from "./ApiKeysList";

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

const { mockListApiKeys, mockCreateApiKey, mockRevokeApiKey, mockToastError } =
  vi.hoisted(() => ({
    mockListApiKeys: vi.fn(),
    mockCreateApiKey: vi.fn(),
    mockRevokeApiKey: vi.fn(),
    mockToastError: vi.fn(),
  }));

vi.mock("#/server/fns/api-keys", () => ({
  listApiKeys: mockListApiKeys,
  createApiKey: mockCreateApiKey,
  revokeApiKey: mockRevokeApiKey,
}));

vi.mock("sonner", () => ({
  toast: { error: mockToastError, success: vi.fn() },
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

describe("ApiKeysList", () => {
  it("mostra estado vazio quando não há chaves (edge)", async () => {
    mockListApiKeys.mockResolvedValue([]);
    renderWithClient(<ApiKeysList />);

    await waitFor(() =>
      expect(screen.getByText("apikeys_empty")).toBeInTheDocument(),
    );
  });

  it("lista as chaves existentes com escopos", async () => {
    mockListApiKeys.mockResolvedValue([
      {
        id: "k1",
        name: "Deploy CI",
        scopes: ["read", "write"],
        created_at: "2026-01-01T00:00:00.000Z",
        last_used_at: null,
      },
    ]);
    renderWithClient(<ApiKeysList />);

    await waitFor(() =>
      expect(screen.getByText("Deploy CI")).toBeInTheDocument(),
    );
    expect(screen.getByText("read")).toBeInTheDocument();
    expect(screen.getByText("write")).toBeInTheDocument();
    expect(screen.getByText("—")).toBeInTheDocument(); // last_used_at null
  });

  it("abre o modal de criação e cria uma chave, exibindo o secret uma única vez", async () => {
    mockListApiKeys.mockResolvedValue([]);
    mockCreateApiKey.mockResolvedValue({ secret: "sk_new_secret" });
    renderWithClient(<ApiKeysList />);
    await waitFor(() => screen.getByText("apikeys_empty"));

    fireEvent.click(screen.getAllByText("apikeys_create_cta")[0]);
    // O label não tem htmlFor/id associado ao input — único textbox do modal.
    // Scope "read" já vem selecionado por padrão (useState inicial) — não
    // precisa (nem deve) clicar nele, ou desmarcaria.
    fireEvent.change(screen.getByRole("textbox"), {
      target: { value: "Nova chave" },
    });

    const createButtons = screen.getAllByText("apikeys_create_cta");
    fireEvent.click(createButtons[createButtons.length - 1]);

    await waitFor(() =>
      expect(screen.getByText("sk_new_secret")).toBeInTheDocument(),
    );
    expect(mockCreateApiKey).toHaveBeenCalledWith({
      data: { name: "Nova chave", scopes: ["read"] },
    });
  });

  it("desabilita o botão de criar quando o nome está vazio (edge)", async () => {
    mockListApiKeys.mockResolvedValue([]);
    renderWithClient(<ApiKeysList />);
    await waitFor(() => screen.getByText("apikeys_empty"));

    fireEvent.click(screen.getAllByText("apikeys_create_cta")[0]);

    const createButtons = screen.getAllByText("apikeys_create_cta");
    const modalCreateButton = createButtons[createButtons.length - 1];
    expect(modalCreateButton.closest("button")).toBeDisabled();
  });

  it("fluxo de revogação exige confirmação antes de chamar a mutation", async () => {
    mockListApiKeys.mockResolvedValue([
      {
        id: "k1",
        name: "Deploy CI",
        scopes: ["read"],
        created_at: "2026-01-01T00:00:00.000Z",
        last_used_at: null,
      },
    ]);
    mockRevokeApiKey.mockResolvedValue({ ok: true });
    renderWithClient(<ApiKeysList />);
    await waitFor(() => screen.getByText("Deploy CI"));

    fireEvent.click(screen.getByTitle("apikeys_revoke_title"));
    expect(mockRevokeApiKey).not.toHaveBeenCalled();

    fireEvent.click(screen.getByText("apikeys_revoke_confirm_cta"));

    await waitFor(() =>
      expect(mockRevokeApiKey).toHaveBeenCalledWith({ data: { id: "k1" } }),
    );
  });

  it("cancelar a revogação não chama a mutation (edge)", async () => {
    mockListApiKeys.mockResolvedValue([
      {
        id: "k1",
        name: "Deploy CI",
        scopes: ["read"],
        created_at: "2026-01-01T00:00:00.000Z",
        last_used_at: null,
      },
    ]);
    renderWithClient(<ApiKeysList />);
    await waitFor(() => screen.getByText("Deploy CI"));

    fireEvent.click(screen.getByTitle("apikeys_revoke_title"));
    fireEvent.click(screen.getByText("form_cancel"));

    expect(mockRevokeApiKey).not.toHaveBeenCalled();
    expect(screen.getByTitle("apikeys_revoke_title")).toBeInTheDocument();
  });
});

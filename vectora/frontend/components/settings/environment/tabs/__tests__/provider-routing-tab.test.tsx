// @vitest-environment jsdom
/**
 * Testes da ProviderRoutingTab (gateways Ollama e OpenRouter).
 *
 * Cobre:
 * - Ollama: lista de modelos registrados (vazia / populada), descoberta
 *   (host inacessível vs. host com modelos), registro/remoção (par de erro).
 * - OpenRouter: key não configurada mostra input; salvar key válida mostra
 *   badge configurada (par de erro: key rejeitada); busca no catálogo com
 *   key configurada e registro; remoção de key.
 */

import { describe, it, expect, vi, afterEach, beforeEach } from "vitest";
import {
  render,
  screen,
  cleanup,
  fireEvent,
  waitFor,
} from "@testing-library/react";
import { ProviderRoutingTab } from "../provider-routing-tab";
import { overwriteGetLocale, baseLocale } from "@/lib/paraglide/runtime";

afterEach(cleanup);
afterEach(() => overwriteGetLocale(() => baseLocale));

function mockFetch(
  handlers: Partial<{
    registered: object[];
    discover: { reachable: boolean; models: object[] };
    registerOk: boolean;
    removeOk: boolean;
    openrouterStatus: { configured: boolean; masked: string };
    openrouterRegistered: object[];
    openrouterCatalog: object[];
    openrouterKeySaveOk: boolean;
    openrouterKeySaveDetail: string;
    openrouterRegisterOk: boolean;
  }>,
) {
  global.fetch = vi
    .fn()
    .mockImplementation((url: string, init?: RequestInit) => {
      const method = init?.method;

      if (url === "/provider-routing/ollama/registered" && !method) {
        return Promise.resolve({
          ok: true,
          json: async () => handlers.registered ?? [],
        } as Response);
      }
      if (url === "/provider-routing/ollama/models") {
        return Promise.resolve({
          ok: true,
          json: async () =>
            handlers.discover ?? { reachable: false, models: [] },
        } as Response);
      }
      if (url === "/provider-routing/ollama/registered" && method === "POST") {
        return Promise.resolve({
          ok: handlers.registerOk ?? true,
          status: handlers.registerOk === false ? 500 : 200,
          json: async () => ({
            id: "new-id",
            tag: "qwen3:8b",
            created_at: "now",
          }),
        } as Response);
      }
      if (
        typeof url === "string" &&
        url.startsWith("/provider-routing/ollama/registered/")
      ) {
        return Promise.resolve({
          ok: handlers.removeOk ?? true,
          status: handlers.removeOk === false ? 500 : 200,
          json: async () => ({ ok: true }),
        } as Response);
      }
      if (url === "/provider-routing/openrouter/status") {
        return Promise.resolve({
          ok: true,
          json: async () =>
            handlers.openrouterStatus ?? { configured: false, masked: "" },
        } as Response);
      }
      if (url === "/provider-routing/openrouter/key" && method === "POST") {
        const ok = handlers.openrouterKeySaveOk ?? true;
        return Promise.resolve({
          ok,
          status: ok ? 200 : 400,
          json: async () =>
            ok
              ? { configured: true, masked: "sk-or-•••cdef" }
              : { detail: handlers.openrouterKeySaveDetail ?? "Key rejeitada" },
        } as Response);
      }
      if (url === "/provider-routing/openrouter/key" && method === "DELETE") {
        return Promise.resolve({
          ok: true,
          json: async () => ({ configured: false, masked: "" }),
        } as Response);
      }
      if (
        typeof url === "string" &&
        url.startsWith("/provider-routing/openrouter/models")
      ) {
        return Promise.resolve({
          ok: true,
          json: async () => ({ models: handlers.openrouterCatalog ?? [] }),
        } as Response);
      }
      if (url === "/provider-routing/openrouter/registered" && !method) {
        return Promise.resolve({
          ok: true,
          json: async () => handlers.openrouterRegistered ?? [],
        } as Response);
      }
      if (
        url === "/provider-routing/openrouter/registered" &&
        method === "POST"
      ) {
        const ok = handlers.openrouterRegisterOk ?? true;
        return Promise.resolve({
          ok,
          status: ok ? 200 : 500,
          json: async () => ({
            id: "or-new-id",
            tag: "openai/gpt-4o",
            created_at: "now",
          }),
        } as Response);
      }
      if (
        typeof url === "string" &&
        url.startsWith("/provider-routing/openrouter/registered/")
      ) {
        return Promise.resolve({
          ok: true,
          json: async () => ({ ok: true }),
        } as Response);
      }
      return Promise.resolve({
        ok: false,
        status: 404,
        json: async () => ({}),
      } as Response);
    });
}

describe("ProviderRoutingTab — Ollama", () => {
  beforeEach(() => {
    overwriteGetLocale(() => "pt");
    mockFetch({ registered: [] });
  });

  it("mostra estado vazio quando nenhum modelo está registrado", async () => {
    render(<ProviderRoutingTab />);
    await waitFor(() => {
      expect(screen.getAllByText(/nenhum modelo registrado/i).length).toBe(2);
    });
  });

  it("lista modelos já registrados", async () => {
    mockFetch({
      registered: [{ id: "1", tag: "qwen3:8b", created_at: "now" }],
    });
    render(<ProviderRoutingTab />);
    await waitFor(() => {
      expect(screen.getByText("qwen3:8b")).toBeTruthy();
    });
  });

  it("descoberta com host inacessível exibe aviso, sem crashar", async () => {
    mockFetch({ registered: [], discover: { reachable: false, models: [] } });
    render(<ProviderRoutingTab />);
    await waitFor(() => screen.getByRole("button", { name: /detectar/i }));
    fireEvent.click(screen.getByRole("button", { name: /detectar/i }));
    await waitFor(() => {
      expect(screen.getByText(/n[ãa]o consegui alcan[çc]ar/i)).toBeTruthy();
    });
  });

  it("descoberta com host acessível lista modelos e permite registrar", async () => {
    mockFetch({
      registered: [],
      discover: {
        reachable: true,
        models: [{ name: "qwen3:8b", size: 123, modified_at: null }],
      },
      registerOk: true,
    });
    render(<ProviderRoutingTab />);
    fireEvent.click(await screen.findByRole("button", { name: /detectar/i }));
    await waitFor(() => screen.getByText("qwen3:8b"));

    fireEvent.click(screen.getByRole("button", { name: /registrar/i }));
    await waitFor(() => {
      expect(screen.getAllByText("qwen3:8b").length).toBeGreaterThan(0);
    });
  });

  it("erro ao registrar exibe mensagem, não trava a UI", async () => {
    mockFetch({
      registered: [],
      discover: {
        reachable: true,
        models: [{ name: "qwen3:8b", size: 123, modified_at: null }],
      },
      registerOk: false,
    });
    render(<ProviderRoutingTab />);
    fireEvent.click(await screen.findByRole("button", { name: /detectar/i }));
    await waitFor(() => screen.getByText("qwen3:8b"));

    fireEvent.click(screen.getByRole("button", { name: /registrar/i }));
    await waitFor(() => {
      expect(screen.getByText(/erro ao registrar/i)).toBeTruthy();
    });
  });

  it("remove um modelo registrado", async () => {
    mockFetch({
      registered: [{ id: "1", tag: "qwen3:8b", created_at: "now" }],
      removeOk: true,
    });
    const { container } = render(<ProviderRoutingTab />);
    await waitFor(() => screen.getByText("qwen3:8b"));

    const removeBtn = container.querySelector(
      "button.hover\\:text-destructive",
    );
    expect(removeBtn).toBeTruthy();
    fireEvent.click(removeBtn!);

    await waitFor(() => {
      expect(screen.queryByText("qwen3:8b")).not.toBeInTheDocument();
    });
  });

  it("erro ao remover mantém o modelo na lista e mostra mensagem", async () => {
    mockFetch({
      registered: [{ id: "1", tag: "qwen3:8b", created_at: "now" }],
      removeOk: false,
    });
    const { container } = render(<ProviderRoutingTab />);
    await waitFor(() => screen.getByText("qwen3:8b"));

    const removeBtn = container.querySelector(
      "button.hover\\:text-destructive",
    );
    fireEvent.click(removeBtn!);

    await waitFor(() => {
      expect(screen.getByText(/erro ao remover/i)).toBeTruthy();
    });
    expect(screen.getByText("qwen3:8b")).toBeTruthy();
  });
});

describe("ProviderRoutingTab — OpenRouter", () => {
  beforeEach(() => {
    overwriteGetLocale(() => "pt");
  });

  it("mostra input de key quando não configurada", async () => {
    mockFetch({ openrouterStatus: { configured: false, masked: "" } });
    render(<ProviderRoutingTab />);
    await waitFor(() => {
      expect(screen.getByPlaceholderText(/sk-or-v1/i)).toBeTruthy();
    });
  });

  it("salva key válida e mostra badge configurada", async () => {
    mockFetch({
      openrouterStatus: { configured: false, masked: "" },
      openrouterKeySaveOk: true,
    });
    render(<ProviderRoutingTab />);
    const input = await screen.findByPlaceholderText(/sk-or-v1/i);
    fireEvent.change(input, { target: { value: "sk-or-v1-abcdef" } });
    fireEvent.click(screen.getByRole("button", { name: /salvar/i }));

    await waitFor(() => {
      expect(screen.getByText(/configurada/i)).toBeTruthy();
      expect(screen.getByText("sk-or-•••cdef")).toBeTruthy();
    });
  });

  it("key rejeitada pela OpenRouter exibe mensagem, não salva", async () => {
    mockFetch({
      openrouterStatus: { configured: false, masked: "" },
      openrouterKeySaveOk: false,
      openrouterKeySaveDetail: "Key rejeitada pela OpenRouter (HTTP 401)",
    });
    render(<ProviderRoutingTab />);
    const input = await screen.findByPlaceholderText(/sk-or-v1/i);
    fireEvent.change(input, { target: { value: "bad-key" } });
    fireEvent.click(screen.getByRole("button", { name: /salvar/i }));

    await waitFor(() => {
      expect(screen.getByText(/key rejeitada/i)).toBeTruthy();
    });
    expect(screen.getByPlaceholderText(/sk-or-v1/i)).toBeTruthy();
  });

  it("com key configurada, busca no catálogo e registra um modelo", async () => {
    mockFetch({
      openrouterStatus: { configured: true, masked: "sk-or-•••cdef" },
      openrouterCatalog: [
        { id: "openai/gpt-4o", name: "GPT-4o", context_length: 128000 },
      ],
      openrouterRegisterOk: true,
    });
    render(<ProviderRoutingTab />);
    const search = await screen.findByPlaceholderText(/buscar modelo/i);
    fireEvent.change(search, { target: { value: "gpt-4o" } });

    await waitFor(
      () => {
        expect(screen.getByText("openai/gpt-4o")).toBeTruthy();
      },
      { timeout: 2000 },
    );

    const registerButtons = screen.getAllByRole("button", {
      name: /^registrar$/i,
    });
    fireEvent.click(registerButtons[0]);

    await waitFor(() => {
      expect(screen.getAllByText("openai/gpt-4o").length).toBeGreaterThan(0);
    });
  });

  it("remove a key configurada", async () => {
    mockFetch({
      openrouterStatus: { configured: true, masked: "sk-or-•••cdef" },
    });
    render(<ProviderRoutingTab />);
    await waitFor(() => screen.getByText("sk-or-•••cdef"));

    fireEvent.click(screen.getByRole("button", { name: /remover key/i }));

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/sk-or-v1/i)).toBeTruthy();
    });
  });
});

// @vitest-environment jsdom
/**
 * Testes da GatewaysTab (gateway Ollama).
 *
 * Cobre:
 * - Lista de modelos registrados (vazia / populada)
 * - Descoberta: host inacessível vs. host com modelos
 * - Registro de um modelo descoberto (par de erro: falha de rede)
 * - Remoção de um modelo registrado (par de erro: falha de rede)
 */

import { describe, it, expect, vi, afterEach, beforeEach } from "vitest";
import {
  render,
  screen,
  cleanup,
  fireEvent,
  waitFor,
} from "@testing-library/react";
import { GatewaysTab } from "../gateways-tab";
import { overwriteGetLocale, baseLocale } from "@/lib/paraglide/runtime";

afterEach(cleanup);
afterEach(() => overwriteGetLocale(() => baseLocale));

function mockFetch(
  handlers: Partial<{
    registered: object[];
    discover: { reachable: boolean; models: object[] };
    registerOk: boolean;
    removeOk: boolean;
  }>,
) {
  global.fetch = vi
    .fn()
    .mockImplementation((url: string, init?: RequestInit) => {
      if (
        url === "/gateways/ollama/registered" &&
        (!init || init.method === undefined)
      ) {
        return Promise.resolve({
          ok: true,
          json: async () => handlers.registered ?? [],
        } as Response);
      }
      if (url === "/gateways/ollama/models") {
        return Promise.resolve({
          ok: true,
          json: async () =>
            handlers.discover ?? { reachable: false, models: [] },
        } as Response);
      }
      if (url === "/gateways/ollama/registered" && init?.method === "POST") {
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
        url.startsWith("/gateways/ollama/registered/")
      ) {
        return Promise.resolve({
          ok: handlers.removeOk ?? true,
          status: handlers.removeOk === false ? 500 : 200,
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

describe("GatewaysTab", () => {
  beforeEach(() => {
    overwriteGetLocale(() => "pt");
    mockFetch({ registered: [] });
  });

  it("mostra estado vazio quando nenhum modelo está registrado", async () => {
    render(<GatewaysTab />);
    await waitFor(() => {
      expect(screen.getByText(/nenhum modelo registrado/i)).toBeTruthy();
    });
  });

  it("lista modelos já registrados", async () => {
    mockFetch({
      registered: [{ id: "1", tag: "qwen3:8b", created_at: "now" }],
    });
    render(<GatewaysTab />);
    await waitFor(() => {
      expect(screen.getByText("qwen3:8b")).toBeTruthy();
    });
  });

  it("descoberta com host inacessível exibe aviso, sem crashar", async () => {
    mockFetch({ registered: [], discover: { reachable: false, models: [] } });
    render(<GatewaysTab />);
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
    render(<GatewaysTab />);
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
    render(<GatewaysTab />);
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
    const { container } = render(<GatewaysTab />);
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
    const { container } = render(<GatewaysTab />);
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

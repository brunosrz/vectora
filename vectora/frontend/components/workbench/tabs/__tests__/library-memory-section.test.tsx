// @vitest-environment jsdom
/**
 * MemorySection — seção Memory Library da Library.
 *
 * Cobre: lista os buckets do catálogo; instalar chama POST /rag-library/install
 * e vira "Installed"; erro/borda: bucket com embed_model diferente do atual
 * mostra aviso de incompatibilidade sem bloquear o botão; falha de instalação
 * (status "error") mostra a mensagem sem quebrar a lista; catálogo vazio
 * mostra o estado vazio específico.
 */
import { describe, it, expect, vi, afterEach, beforeEach } from "vitest";
import {
  render,
  screen,
  cleanup,
  waitFor,
  fireEvent,
} from "@testing-library/react";

import { MemorySection } from "../library-memory-section";

afterEach(cleanup);

const CATALOG = [
  {
    id: "b1",
    name: "Bucket 1",
    description: "Documentação interna vetorizada",
    embed_model: "embed-multilingual-v3.0",
    verified: true,
    downloads_count: 42,
    license: "MIT",
  },
  {
    id: "b2",
    name: "Bucket 2",
    description: "Outro bucket comunitário",
    embed_model: "voyage-3",
    verified: false,
    downloads_count: 3,
    license: "MIT",
  },
];

function mockFetch({
  catalog = CATALOG as typeof CATALOG,
  installStatus = "installed" as string,
} = {}) {
  global.fetch = vi
    .fn()
    .mockImplementation((url: string, init?: RequestInit) => {
      if (url === "/rag-library/catalog") {
        return Promise.resolve({
          ok: true,
          json: async () => catalog,
        } as Response);
      }
      if (url === "/rag-library/install" && init?.method === "POST") {
        return Promise.resolve({
          ok: true,
          json: async () =>
            installStatus === "error"
              ? { status: "error", error: "falha ao instalar" }
              : { status: installStatus, collection: "shared_b1" },
        } as Response);
      }
      return Promise.resolve({ ok: true, json: async () => ({}) } as Response);
    });
}

describe("MemorySection", () => {
  beforeEach(() => {
    mockFetch();
  });

  it("lista os buckets do catálogo", async () => {
    render(<MemorySection query="" onCountChange={() => {}} />);
    await waitFor(() => {
      expect(screen.getByText("Bucket 1")).toBeTruthy();
      expect(screen.getByText("Bucket 2")).toBeTruthy();
    });
  });

  it("reporta a contagem filtrada via onCountChange", async () => {
    const onCountChange = vi.fn();
    render(<MemorySection query="" onCountChange={onCountChange} />);
    await waitFor(() => {
      expect(onCountChange).toHaveBeenCalledWith(2);
    });
  });

  it("instalar um bucket chama POST /rag-library/install e vira Installed", async () => {
    render(<MemorySection query="" onCountChange={() => {}} />);
    await waitFor(() => expect(screen.getByText("Bucket 1")).toBeTruthy());

    const card = screen.getByText("Bucket 1").closest("div.rounded-lg")!;
    fireEvent.click(
      Array.from(card.querySelectorAll("button")).find((b) =>
        b.textContent?.includes("Install"),
      )!,
    );

    await waitFor(() => {
      const calls = (global.fetch as ReturnType<typeof vi.fn>).mock.calls;
      expect(
        calls.some(
          (c) => c[0] === "/rag-library/install" && c[1]?.method === "POST",
        ),
      ).toBe(true);
      expect(screen.getByText("Installed")).toBeTruthy();
    });
  });

  it("erro/borda: bucket com embed_model incompatível mostra aviso sem bloquear instalação", async () => {
    render(
      <MemorySection
        query=""
        onCountChange={() => {}}
        currentEmbedModel="embed-multilingual-v3.0"
      />,
    );
    await waitFor(() => expect(screen.getByText("Bucket 2")).toBeTruthy());

    expect(screen.getAllByText(/voyage-3/).length).toBeGreaterThan(0);
    const card = screen.getByText("Bucket 2").closest("div.rounded-lg")!;
    const installButton = Array.from(card.querySelectorAll("button")).find(
      (b) => b.textContent?.includes("Install"),
    )!;
    expect(installButton.hasAttribute("disabled")).toBe(false);
  });

  it("erro/borda: falha de instalação (status 'error') mostra mensagem sem quebrar a lista", async () => {
    mockFetch({ installStatus: "error" });
    render(<MemorySection query="" onCountChange={() => {}} />);
    await waitFor(() => expect(screen.getByText("Bucket 1")).toBeTruthy());

    const card = screen.getByText("Bucket 1").closest("div.rounded-lg")!;
    fireEvent.click(
      Array.from(card.querySelectorAll("button")).find((b) =>
        b.textContent?.includes("Install"),
      )!,
    );

    await waitFor(() => {
      expect(screen.getByText("falha ao instalar")).toBeTruthy();
    });
    expect(screen.getByText("Bucket 2")).toBeTruthy();
  });

  it("erro/borda: catálogo vazio mostra o estado vazio específico", async () => {
    mockFetch({ catalog: [] });
    render(<MemorySection query="" onCountChange={() => {}} />);
    await waitFor(() => {
      expect(screen.getByText(/no memory buckets/i)).toBeTruthy();
    });
  });
});

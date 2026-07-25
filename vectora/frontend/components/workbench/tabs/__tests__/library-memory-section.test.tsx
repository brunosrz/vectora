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
import { useLibraryStore } from "@/lib/stores/library-store";
import { useWorkspacesStore } from "@/lib/stores/workspaces-store";

afterEach(cleanup);

beforeEach(() => {
  useLibraryStore.setState({
    memoryItems: [],
    memoryLoading: false,
    memoryFetchedAt: null,
  });
  useWorkspacesStore.setState({ workspaces: [], active_id: null });
});

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
  licenseConfigured = false,
  publishStatus = "published" as string,
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
      if (url === "/rag-library/publish" && init?.method === "POST") {
        return Promise.resolve({
          ok: true,
          json: async () =>
            publishStatus === "error"
              ? { status: "error", error: "falha ao publicar" }
              : { status: "published", bucket_id: "b-new" },
        } as Response);
      }
      if (url === "/license/status") {
        return Promise.resolve({
          ok: true,
          json: async () => ({ configured: licenseConfigured }),
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

  it("sem conta vectora.company conectada, mostra a nota em vez do botão de publicar", async () => {
    mockFetch({ licenseConfigured: false });
    useWorkspacesStore.setState({
      workspaces: [
        {
          id: "ws1",
          name: "ws",
          cwd: "/x",
          trusted: true,
          is_git_repo: false,
          git_remote: null,
          git_current_branch: null,
          git_default_branch: null,
        },
      ],
      active_id: "ws1",
    });
    render(<MemorySection query="" onCountChange={() => {}} />);
    await waitFor(() =>
      expect(
        screen.getByText(/Publishing from the app will be available/),
      ).toBeTruthy(),
    );
    expect(screen.queryByText("Publish my memory")).toBeNull();
  });

  it("com conta conectada e workspace ativo, publica pelo diálogo (POST /rag-library/publish)", async () => {
    mockFetch({ licenseConfigured: true, publishStatus: "published" });
    useWorkspacesStore.setState({
      workspaces: [
        {
          id: "ws1",
          name: "ws",
          cwd: "/x",
          trusted: true,
          is_git_repo: false,
          git_remote: null,
          git_current_branch: null,
          git_default_branch: null,
        },
      ],
      active_id: "ws1",
    });
    render(<MemorySection query="" onCountChange={() => {}} />);

    await waitFor(() =>
      expect(screen.getByText("Publish my memory")).toBeTruthy(),
    );
    fireEvent.click(screen.getByText("Publish my memory"));

    await waitFor(() =>
      expect(screen.getByText("Publish memory")).toBeTruthy(),
    );
    fireEvent.change(screen.getByLabelText("Name"), {
      target: { value: "Meus docs" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Publish" }));

    await waitFor(() => {
      const calls = (global.fetch as ReturnType<typeof vi.fn>).mock.calls;
      const publishCall = calls.find(
        (c) => c[0] === "/rag-library/publish" && c[1]?.method === "POST",
      );
      expect(publishCall).toBeTruthy();
      const body = JSON.parse(publishCall![1].body as string);
      expect(body).toMatchObject({ workspace_id: "ws1", name: "Meus docs" });
    });
  });

  it("erro/borda: falha ao publicar mostra a mensagem sem fechar o diálogo", async () => {
    mockFetch({ licenseConfigured: true, publishStatus: "error" });
    useWorkspacesStore.setState({
      workspaces: [
        {
          id: "ws1",
          name: "ws",
          cwd: "/x",
          trusted: true,
          is_git_repo: false,
          git_remote: null,
          git_current_branch: null,
          git_default_branch: null,
        },
      ],
      active_id: "ws1",
    });
    render(<MemorySection query="" onCountChange={() => {}} />);

    await waitFor(() =>
      expect(screen.getByText("Publish my memory")).toBeTruthy(),
    );
    fireEvent.click(screen.getByText("Publish my memory"));
    await waitFor(() =>
      expect(screen.getByText("Publish memory")).toBeTruthy(),
    );
    fireEvent.change(screen.getByLabelText("Name"), {
      target: { value: "Meus docs" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Publish" }));

    await waitFor(() => {
      expect(screen.getByText("falha ao publicar")).toBeTruthy();
    });
    expect(screen.getByText("Publish memory")).toBeTruthy();
  });
});

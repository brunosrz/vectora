// @vitest-environment jsdom
/**
 * WorkspaceTrustDialog: botão de reload recarrega o diretório listado, e o
 * fluxo de "nova pasta" cria a subpasta via POST e relista (par feliz),
 * mostrando erro localizado em conflito de nome (par de erro).
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  render,
  screen,
  cleanup,
  fireEvent,
  waitFor,
} from "@testing-library/react";

import { WorkspaceTrustDialog } from "../workspace-trust-dialog";

const FETCH = vi.fn();

function jsonRes(body: unknown, status = 200) {
  return Promise.resolve(
    new Response(JSON.stringify(body), {
      status,
      headers: { "Content-Type": "application/json" },
    }),
  );
}

const listing = {
  path: "C:\\Users\\Machi\\Documents\\vectora",
  parent: "C:\\Users\\Machi\\Documents",
  entries: [
    {
      name: "projeto-a",
      path: "C:\\...\\projeto-a",
      is_dir: true,
      kind: "dir",
    },
  ],
  safe_root_id: "docs-vectora",
  at_drives_root: false,
};

beforeEach(() => {
  Object.defineProperty(window.navigator, "onLine", {
    value: true,
    writable: true,
    configurable: true,
  });
  FETCH.mockReset();
  FETCH.mockImplementation((url: string) => {
    if (url.startsWith("/workspaces/browse/mkdir")) {
      return jsonRes({ error: "unhandled mkdir call" }, 500);
    }
    if (url.startsWith("/workspaces/browse")) {
      return jsonRes(listing);
    }
    return jsonRes({}, 404);
  });
  vi.stubGlobal("fetch", FETCH);
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("WorkspaceTrustDialog — reload e nova pasta", () => {
  it("botão de reload refaz o fetch do diretório atualmente listado", async () => {
    render(<WorkspaceTrustDialog open onOpenChange={() => {}} />);

    await waitFor(() => screen.getByText("projeto-a"));
    const callsBeforeReload = FETCH.mock.calls.length;

    fireEvent.click(screen.getByTitle("Reload"));

    await waitFor(() =>
      expect(FETCH.mock.calls.length).toBeGreaterThan(callsBeforeReload),
    );
    const lastCall = FETCH.mock.calls.at(-1)?.[0] as string;
    expect(lastCall).toContain("/workspaces/browse");
    expect(lastCall).toContain(encodeURIComponent(listing.path));
  });

  it("cria uma pasta nova e relista (feliz); nome em conflito mostra erro sem travar o formulário (edge)", async () => {
    FETCH.mockImplementation((url: string, init?: RequestInit) => {
      if (url === "/workspaces/browse/mkdir" && init?.method === "POST") {
        const body = JSON.parse(init.body as string) as {
          path: string;
          name: string;
        };
        if (body.name === "ja-existe") {
          return jsonRes({ detail: "conflict" }, 409);
        }
        return jsonRes({
          ...listing,
          entries: [
            ...listing.entries,
            {
              name: body.name,
              path: `${body.path}\\${body.name}`,
              is_dir: true,
              kind: "dir",
            },
          ],
        });
      }
      if (url.startsWith("/workspaces/browse")) {
        return jsonRes(listing);
      }
      return jsonRes({}, 404);
    });

    render(<WorkspaceTrustDialog open onOpenChange={() => {}} />);
    await waitFor(() => screen.getByText("projeto-a"));

    fireEvent.click(screen.getByTitle("New folder"));
    const input = await screen.findByPlaceholderText("Folder name");
    fireEvent.change(input, { target: { value: "minha-pasta" } });
    fireEvent.click(screen.getByText("Create"));

    await waitFor(() => screen.getByText("minha-pasta"));
    // Formulário fecha após sucesso.
    expect(screen.queryByPlaceholderText("Folder name")).toBeNull();

    // Edge — conflito: reabre o formulário e tenta um nome já existente.
    fireEvent.click(screen.getByTitle("New folder"));
    const input2 = await screen.findByPlaceholderText("Folder name");
    fireEvent.change(input2, { target: { value: "ja-existe" } });
    fireEvent.click(screen.getByText("Create"));

    await waitFor(() =>
      screen.getByText("A folder with that name already exists."),
    );
    // Formulário continua aberto — usuário pode corrigir o nome.
    expect(screen.getByPlaceholderText("Folder name")).toBeTruthy();
  });
});

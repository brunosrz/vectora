// @vitest-environment jsdom
/**
 * PreviewTab — o iframe só navega quando o backend confirma a porta aberta
 * (running=true), nunca só porque o processo do dev server existe. Cobre o
 * bug reproduzido ao vivo: ERR_CONNECTION_REFUSED por navegar cedo demais
 * pra um `vite`/`next` ainda compilando.
 */
import { describe, it, expect, vi, afterEach } from "vitest";
import {
  render,
  screen,
  cleanup,
  waitFor,
  fireEvent,
} from "@testing-library/react";

import { PreviewTab } from "../preview-tab";

vi.mock("@/lib/paraglide/messages", () => ({
  m: new Proxy(
    {},
    {
      get:
        (_t, prop) =>
        (...args: unknown[]) =>
          args.length
            ? `${String(prop)}(${JSON.stringify(args[0])})`
            : String(prop),
    },
  ),
}));

vi.mock("@/lib/stores/workspaces-store", () => ({
  useWorkspacesStore: (
    sel: (s: { getActive: () => { id: string } | undefined }) => unknown,
  ) => sel({ getActive: () => ({ id: "ws1" }) }),
}));

vi.mock("@/lib/stores/chat-input-store", () => ({
  useChatInputStore: { getState: () => ({ pushDraft: vi.fn() }) },
}));

afterEach(cleanup);

const LAUNCH = {
  version: "0.0.1",
  configurations: [
    {
      name: "web",
      runtimeExecutable: "npm",
      runtimeArgs: ["run", "dev"],
      port: 3001,
    },
  ],
};

function mockFetch({
  startRunning = false,
  logLines,
}: {
  startRunning?: boolean;
  logLines?: string[];
} = {}) {
  global.fetch = vi
    .fn()
    .mockImplementation((url: string, init?: RequestInit) => {
      if (
        url.endsWith("/preview/launch") &&
        (!init || init.method === undefined)
      ) {
        return Promise.resolve({
          ok: true,
          json: async () => LAUNCH,
        } as Response);
      }
      if (url.endsWith("/preview/status")) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            servers: [
              {
                name: "web",
                port: 3001,
                running: startRunning,
                pid: startRunning ? 1 : null,
              },
            ],
          }),
        } as Response);
      }
      if (url.endsWith("/preview/start")) {
        return Promise.resolve({
          ok: true,
          json: async () => ({ status: "ok" }),
        } as Response);
      }
      if (url.includes("/preview/logs")) {
        return Promise.resolve({
          ok: true,
          json: async () => ({ lines: logLines ?? [] }),
        } as Response);
      }
      return Promise.resolve({ ok: true, json: async () => ({}) } as Response);
    });
}

describe("PreviewTab", () => {
  it("clicar em iniciar com backend ainda compilando mostra estado 'iniciando', sem navegar o iframe", async () => {
    mockFetch({ startRunning: false });
    render(<PreviewTab threadId="t1" />);

    const startBtn = await screen.findByTitle("workbench_preview_start");
    fireEvent.click(startBtn);

    await waitFor(() => {
      expect(screen.getByText("workbench_preview_starting")).toBeTruthy();
    });
    expect(document.querySelector("iframe")).toBeNull();
  });

  it("com a porta já aberta (status inicial), clicar em 'abrir' navega o iframe pra localhost:<port>", async () => {
    mockFetch({ startRunning: true });
    render(<PreviewTab threadId="t1" />);

    // O poll inicial de /preview/status já reporta running=true — o botão
    // "abrir" (ExternalLink) só existe quando isRunning é true.
    const openBtn = await screen.findByTitle("workbench_preview_open_preview");
    fireEvent.click(openBtn);

    const iframe = await screen.findByTitle("Live Preview");
    expect(iframe.getAttribute("src")).toBe("http://localhost:3001");
  });

  it("botão de console abre o painel e mostra as linhas de log do servidor", async () => {
    mockFetch({ startRunning: false, logLines: ["compiling...", "ready"] });
    render(<PreviewTab threadId="t1" />);

    const consoleBtn = await screen.findByTitle("workbench_preview_console");
    fireEvent.click(consoleBtn);

    await waitFor(() => {
      expect(screen.getByText("compiling...")).toBeTruthy();
      expect(screen.getByText("ready")).toBeTruthy();
    });
  });

  it("servidor nunca iniciado mostra estado vazio específico do console, não erro", async () => {
    mockFetch({ startRunning: false, logLines: [] });
    render(<PreviewTab threadId="t1" />);

    const consoleBtn = await screen.findByTitle("workbench_preview_console");
    fireEvent.click(consoleBtn);

    await waitFor(() => {
      expect(screen.getByText("workbench_preview_console_empty")).toBeTruthy();
    });
  });
});

// @vitest-environment jsdom
/**
 * BrowserTab — navegação livre (barra de URL sempre ativa, histórico
 * voltar/avançar) e paridade com o antigo PreviewTab: servidores de dev
 * do workspace continuam iniciando/parando/logando, agora como atalhos
 * dentro do mesmo painel. Cobre o bug original (iframe só navega quando o
 * backend confirma a porta aberta, nunca só porque o processo existe) e
 * as novas capacidades (URL externa sem servidor configurado, back/forward).
 */
import { describe, it, expect, vi, afterEach } from "vitest";
import {
  render,
  screen,
  cleanup,
  waitFor,
  fireEvent,
} from "@testing-library/react";

import { BrowserTab } from "../browser-tab";

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
  configurations = LAUNCH.configurations,
  startRunning = false,
  logLines,
}: {
  configurations?: typeof LAUNCH.configurations;
  startRunning?: boolean;
  logLines?: string[];
} = {}) {
  global.fetch = vi
    .fn()
    .mockImplementation((url: string, init?: RequestInit) => {
      if (
        url.endsWith("/browser/launch") &&
        (!init || init.method === undefined)
      ) {
        return Promise.resolve({
          ok: true,
          json: async () => ({ version: "0.0.1", configurations }),
        } as Response);
      }
      if (url.endsWith("/browser/status")) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            servers: configurations.map((c) => ({
              name: c.name,
              port: c.port,
              running: startRunning,
              pid: startRunning ? 1 : null,
            })),
          }),
        } as Response);
      }
      if (url.endsWith("/browser/start")) {
        return Promise.resolve({
          ok: true,
          json: async () => ({ status: "ok" }),
        } as Response);
      }
      if (url.includes("/browser/logs")) {
        return Promise.resolve({
          ok: true,
          json: async () => ({ lines: logLines ?? [] }),
        } as Response);
      }
      return Promise.resolve({ ok: true, json: async () => ({}) } as Response);
    });
}

describe("BrowserTab — servidores de dev (paridade com o antigo Preview)", () => {
  it("clicar em iniciar com backend ainda compilando não navega o iframe (nenhuma porta aberta ainda)", async () => {
    mockFetch({ startRunning: false });
    render(<BrowserTab threadId="t1" />);

    const startBtn = await screen.findByTitle("workbench_browser_start");
    fireEvent.click(startBtn);

    await waitFor(() => {
      expect(document.querySelector("iframe")).toBeNull();
    });
  });

  it("com a porta já aberta (status inicial), clicar em 'abrir servidor' navega o iframe pra localhost:<port>", async () => {
    mockFetch({ startRunning: true });
    render(<BrowserTab threadId="t1" />);

    const openBtn = await screen.findByTitle("workbench_browser_open_server");
    fireEvent.click(openBtn);

    const iframe = await screen.findByTitle("Browser");
    expect(iframe.getAttribute("src")).toBe("http://localhost:3001");
  });

  it("botão de console abre o painel e mostra as linhas de log do servidor", async () => {
    mockFetch({ startRunning: false, logLines: ["compiling...", "ready"] });
    render(<BrowserTab threadId="t1" />);

    const consoleBtn = await screen.findByTitle("workbench_browser_console");
    fireEvent.click(consoleBtn);

    await waitFor(() => {
      expect(screen.getByText("compiling...")).toBeTruthy();
      expect(screen.getByText("ready")).toBeTruthy();
    });
  });

  it("servidor nunca iniciado mostra estado vazio específico do console, não erro", async () => {
    mockFetch({ startRunning: false, logLines: [] });
    render(<BrowserTab threadId="t1" />);

    const consoleBtn = await screen.findByTitle("workbench_browser_console");
    fireEvent.click(consoleBtn);

    await waitFor(() => {
      expect(screen.getByText("workbench_browser_console_empty")).toBeTruthy();
    });
  });
});

describe("BrowserTab — navegação livre (sem depender de servidor configurado)", () => {
  it("digitar uma URL externa e pressionar Enter navega o iframe, mesmo sem nenhum servidor configurado", async () => {
    mockFetch({ configurations: [] });
    render(<BrowserTab threadId="t1" />);

    const urlBar = await screen.findByTestId("browser-url-bar");
    fireEvent.focus(urlBar);
    fireEvent.change(urlBar, { target: { value: "google.com" } });
    fireEvent.keyDown(urlBar, { key: "Enter" });

    const iframe = await screen.findByTitle("Browser");
    expect(iframe.getAttribute("src")).toBe("https://google.com");
  });

  it("sem nenhuma URL navegada e sem servidores configurados, mostra o estado vazio com onboarding (pedir ao agente / adicionar manualmente)", async () => {
    mockFetch({ configurations: [] });
    render(<BrowserTab threadId="t1" />);

    await waitFor(() => {
      expect(screen.getByText("workbench_browser_empty_title")).toBeTruthy();
    });
    expect(screen.getByText("workbench_browser_ask_agent")).toBeTruthy();
    expect(document.querySelector("iframe")).toBeNull();
  });
});

describe("BrowserTab — histórico voltar/avançar", () => {
  it("voltar/avançar navegam entre URLs visitadas; avançar fica desabilitado até haver histórico à frente", async () => {
    mockFetch({ configurations: [] });
    render(<BrowserTab threadId="t1" />);

    const urlBar = await screen.findByTestId("browser-url-bar");
    fireEvent.focus(urlBar);
    fireEvent.change(urlBar, { target: { value: "example.com" } });
    fireEvent.keyDown(urlBar, { key: "Enter" });
    await screen.findByTitle("Browser");

    fireEvent.focus(urlBar);
    fireEvent.change(urlBar, { target: { value: "example.org" } });
    fireEvent.keyDown(urlBar, { key: "Enter" });
    await waitFor(() => {
      expect(document.querySelector("iframe")?.getAttribute("src")).toBe(
        "https://example.org",
      );
    });

    const backBtn = screen.getByTitle("workbench_browser_back");
    fireEvent.click(backBtn);
    await waitFor(() => {
      expect(document.querySelector("iframe")?.getAttribute("src")).toBe(
        "https://example.com",
      );
    });

    const forwardBtn = screen.getByTitle("workbench_browser_forward");
    fireEvent.click(forwardBtn);
    await waitFor(() => {
      expect(document.querySelector("iframe")?.getAttribute("src")).toBe(
        "https://example.org",
      );
    });
  });

  it("navegar pra uma nova URL depois de voltar descarta o ramo antigo do histórico (avançar fica desabilitado)", async () => {
    mockFetch({ configurations: [] });
    render(<BrowserTab threadId="t1" />);

    const urlBar = await screen.findByTestId("browser-url-bar");
    fireEvent.focus(urlBar);
    fireEvent.change(urlBar, { target: { value: "example.com" } });
    fireEvent.keyDown(urlBar, { key: "Enter" });
    await screen.findByTitle("Browser");

    fireEvent.focus(urlBar);
    fireEvent.change(urlBar, { target: { value: "example.org" } });
    fireEvent.keyDown(urlBar, { key: "Enter" });
    await waitFor(() => {
      expect(document.querySelector("iframe")?.getAttribute("src")).toBe(
        "https://example.org",
      );
    });

    fireEvent.click(screen.getByTitle("workbench_browser_back"));
    await waitFor(() => {
      expect(document.querySelector("iframe")?.getAttribute("src")).toBe(
        "https://example.com",
      );
    });

    fireEvent.focus(urlBar);
    fireEvent.change(urlBar, { target: { value: "example.net" } });
    fireEvent.keyDown(urlBar, { key: "Enter" });
    await waitFor(() => {
      expect(document.querySelector("iframe")?.getAttribute("src")).toBe(
        "https://example.net",
      );
    });

    const forwardBtn = screen.getByTitle("workbench_browser_forward");
    expect(forwardBtn).toBeDisabled();
  });
});

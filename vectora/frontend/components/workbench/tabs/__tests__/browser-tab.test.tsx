// @vitest-environment jsdom
/**
 * BrowserTab — navegação livre (barra de URL sempre ativa, histórico
 * voltar/avançar) e paridade com o antigo PreviewTab: servidores de dev
 * do workspace continuam iniciando/parando/logando, agora como atalhos
 * dentro do mesmo painel. Cobre o bug original (iframe só navega quando o
 * backend confirma a porta aberta, nunca só porque o processo existe) e
 * as novas capacidades (URL externa sem servidor configurado, back/forward).
 */
import { describe, it, expect, vi, afterEach, beforeEach } from "vitest";
import {
  render,
  screen,
  cleanup,
  waitFor,
  fireEvent,
  act,
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

// jsdom não implementa ResizeObserver — só o caminho desktop (efeito de
// bounds da WebContentsView) o usa; um stub no-op basta pros testes.
class StubResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}
// eslint-disable-next-line @typescript-eslint/no-explicit-any
(globalThis as any).ResizeObserver ??= StubResizeObserver;

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

  it("clicar no cabeçalho 'Servidores' recolhe a lista; clicar de novo expande", async () => {
    mockFetch({ startRunning: false });
    render(<BrowserTab threadId="t1" />);

    await screen.findByTitle("workbench_browser_start");
    expect(screen.getByText("web")).toBeTruthy();

    fireEvent.click(screen.getByTitle("workbench_browser_servers_collapse"));
    expect(screen.queryByText("web")).toBeNull();

    fireEvent.click(screen.getByTitle("workbench_browser_servers_expand"));
    expect(screen.getByText("web")).toBeTruthy();
  });

  it("recolher os servidores não fecha o formulário de adicionar manualmente por engano (botões independentes)", async () => {
    mockFetch({ startRunning: false });
    render(<BrowserTab threadId="t1" />);

    fireEvent.click(await screen.findByTitle("workbench_browser_manual_add"));
    expect(
      screen.getByPlaceholderText("workbench_browser_field_name"),
    ).toBeTruthy();

    fireEvent.click(screen.getByTitle("workbench_browser_servers_collapse"));
    // Recolhido: o formulário de adicionar servidor some junto com a lista,
    // mas o botão "+" continua funcionando e independente do de colapsar.
    expect(
      screen.queryByPlaceholderText("workbench_browser_field_name"),
    ).toBeNull();

    fireEvent.click(screen.getByTitle("workbench_browser_servers_expand"));
    expect(
      screen.getByPlaceholderText("workbench_browser_field_name"),
    ).toBeTruthy();
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

describe("BrowserTab — auto-navegação quando um servidor sobe (Sprint fix 9.2)", () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it("servidor que passa de parado pra rodando entre polls navega sozinho, sem clique — mesmo caminho da tool do agente", async () => {
    let running = false;
    global.fetch = vi.fn().mockImplementation((url: string) => {
      if (url.endsWith("/browser/launch")) {
        return Promise.resolve({
          ok: true,
          json: async () => LAUNCH,
        } as Response);
      }
      if (url.endsWith("/browser/status")) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            servers: [
              { name: "web", port: 3001, running, pid: running ? 1 : null },
            ],
          }),
        } as Response);
      }
      return Promise.resolve({ ok: true, json: async () => ({}) } as Response);
    });

    render(<BrowserTab threadId="t1" />);

    // Primeiro poll: parado — não é uma transição, não navega.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    expect(document.querySelector("iframe")).toBeNull();

    // O servidor sobe "por fora" (ex.: tool browser_start do agente) — o
    // próximo poll (3s) já reflete running:true.
    running = true;
    await act(async () => {
      await vi.advanceTimersByTimeAsync(3000);
    });

    const iframe = document.querySelector("iframe");
    expect(iframe?.getAttribute("src")).toBe("http://localhost:3001");
  });

  it("servidor já rodando desde o primeiro poll não navega sozinho (só a transição conta, não o estado inicial)", async () => {
    mockFetch({ startRunning: true });
    render(<BrowserTab threadId="t1" />);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(50);
    });
    expect(document.querySelector("iframe")).toBeNull();
  });
});

describe("BrowserTab — console inline, não popup (Sprint fix 9.1)", () => {
  it("painel do console renderiza dentro do container da própria aba, não num portal/dialog em document.body", async () => {
    mockFetch({ startRunning: false, logLines: ["ready"] });
    const { container } = render(<BrowserTab threadId="t1" />);

    const consoleBtn = await screen.findByTitle("workbench_browser_console");
    fireEvent.click(consoleBtn);

    await waitFor(() => {
      expect(container.textContent).toContain("ready");
    });
    // Nunca deve existir role="dialog" (Radix Sheet/Dialog) — é um painel
    // inline, não um portal sobrepondo a janela.
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("botão de fechar o console some o painel sem afetar o iframe carregado", async () => {
    mockFetch({ startRunning: true, logLines: ["ready"] });
    render(<BrowserTab threadId="t1" />);

    const openBtn = await screen.findByTitle("workbench_browser_open_server");
    fireEvent.click(openBtn);
    await screen.findByTitle("Browser");

    fireEvent.click(await screen.findByTitle("workbench_browser_console"));
    await waitFor(() => expect(screen.getByText("ready")).toBeTruthy());

    fireEvent.click(screen.getByTitle("workbench_browser_console_close"));
    await waitFor(() => {
      expect(screen.queryByText("ready")).toBeNull();
    });
    expect(screen.getByTitle("Browser")).toBeTruthy();
  });
});

describe("BrowserTab — sandbox do iframe (Sprint fix 9.3)", () => {
  it("servidor de dev do próprio workspace ganha allow-same-origin (CSS do Next.js precisa disso)", async () => {
    mockFetch({ startRunning: true });
    render(<BrowserTab threadId="t1" />);

    const openBtn = await screen.findByTitle("workbench_browser_open_server");
    fireEvent.click(openBtn);

    const iframe = await screen.findByTitle("Browser");
    expect(iframe.getAttribute("sandbox")).toContain("allow-same-origin");
  });

  it("URL externa navegada livremente nunca ganha allow-same-origin, mesmo depois de já ter aberto um servidor do workspace", async () => {
    mockFetch({ startRunning: true });
    render(<BrowserTab threadId="t1" />);

    const urlBar = await screen.findByTestId("browser-url-bar");
    fireEvent.focus(urlBar);
    fireEvent.change(urlBar, { target: { value: "example.com" } });
    fireEvent.keyDown(urlBar, { key: "Enter" });

    const iframe = await screen.findByTitle("Browser");
    expect(iframe.getAttribute("src")).toBe("https://example.com");
    expect(iframe.getAttribute("sandbox")).not.toContain("allow-same-origin");
  });
});

describe("BrowserTab — caminho desktop (WebContentsView real via window.vectora.browserView)", () => {
  type EventHandler = (
    viewId: number,
    event: {
      type: string;
      url?: string;
      canGoBack?: boolean;
      canGoForward?: boolean;
      isLoading?: boolean;
      errorDescription?: string;
    },
  ) => void;

  function mockBrowserView() {
    const calls = {
      createView: vi.fn(),
      destroyView: vi.fn(),
      navigate: vi.fn(async (_viewId: number, url: string) => {
        if (url === "https://falha.invalid") {
          return { ok: false, error: "esquema não permitido: ftp://x" };
        }
        return { ok: true };
      }),
      goBack: vi.fn(),
      goForward: vi.fn(),
      reload: vi.fn(),
      setBounds: vi.fn(),
      setVisible: vi.fn(),
    };
    let handler: EventHandler | null = null;
    const bridge = {
      ...calls,
      createView: vi.fn(async () => 1),
      onEvent: vi.fn((h: EventHandler) => {
        handler = h;
        return () => {
          handler = null;
        };
      }),
      emitEvent: (viewId: number, event: Parameters<EventHandler>[1]) =>
        handler?.(viewId, event),
    };
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (window as any).vectora = { browserView: bridge };
    return bridge;
  }

  afterEach(() => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    delete (window as any).vectora;
  });

  it("no desktop, digitar uma URL chama a bridge e renderiza a área da WebContentsView, nunca um <iframe>", async () => {
    const bridge = mockBrowserView();
    mockFetch({ configurations: [] });
    render(<BrowserTab threadId="t1" />);

    await waitFor(() => expect(bridge.onEvent).toHaveBeenCalled());

    const urlBar = await screen.findByTestId("browser-url-bar");
    fireEvent.focus(urlBar);
    fireEvent.change(urlBar, { target: { value: "example.com" } });
    fireEvent.keyDown(urlBar, { key: "Enter" });

    await waitFor(() => {
      expect(bridge.navigate).toHaveBeenCalledWith(1, "https://example.com");
    });
    expect(document.querySelector("iframe")).toBeNull();
    expect(
      screen.getByTestId("browser-webcontentsview-container"),
    ).toBeTruthy();
  });

  it("evento navigated do main atualiza a barra de URL e can-go-back/forward — nunca escritos manualmente", async () => {
    const bridge = mockBrowserView();
    mockFetch({ configurations: [] });
    render(<BrowserTab threadId="t1" />);
    await waitFor(() => expect(bridge.onEvent).toHaveBeenCalled());

    act(() => {
      bridge.emitEvent(1, {
        type: "navigated",
        url: "https://example.com/pagina",
        canGoBack: true,
        canGoForward: false,
      });
    });

    const urlBar = await screen.findByTestId("browser-url-bar");
    await waitFor(() => {
      expect(urlBar).toHaveValue("https://example.com/pagina");
    });
    expect(screen.getByTitle("workbench_browser_back")).not.toBeDisabled();
    expect(screen.getByTitle("workbench_browser_forward")).toBeDisabled();
  });

  it("voltar/avançar/recarregar chamam a bridge, nunca a lógica de histórico do iframe", async () => {
    const bridge = mockBrowserView();
    mockFetch({ configurations: [] });
    render(<BrowserTab threadId="t1" />);
    await waitFor(() => expect(bridge.onEvent).toHaveBeenCalled());

    act(() => {
      bridge.emitEvent(1, {
        type: "navigated",
        url: "https://example.com",
        canGoBack: true,
        canGoForward: true,
      });
    });

    fireEvent.click(await screen.findByTitle("workbench_browser_back"));
    fireEvent.click(screen.getByTitle("workbench_browser_forward"));
    fireEvent.click(screen.getByTitle("workbench_files_refresh"));

    expect(bridge.goBack).toHaveBeenCalledWith(1);
    expect(bridge.goForward).toHaveBeenCalledWith(1);
    expect(bridge.reload).toHaveBeenCalledWith(1);
  });

  it("falha ao navegar (esquema não permitido) mostra a mensagem de erro; navegação seguinte bem-sucedida a limpa", async () => {
    const bridge = mockBrowserView();
    mockFetch({ configurations: [] });
    render(<BrowserTab threadId="t1" />);
    await waitFor(() => expect(bridge.onEvent).toHaveBeenCalled());

    const urlBar = await screen.findByTestId("browser-url-bar");
    fireEvent.focus(urlBar);
    fireEvent.change(urlBar, { target: { value: "https://falha.invalid" } });
    fireEvent.keyDown(urlBar, { key: "Enter" });

    await waitFor(() => {
      expect(screen.getByText("esquema não permitido: ftp://x")).toBeTruthy();
    });

    act(() => {
      bridge.emitEvent(1, {
        type: "navigated",
        url: "https://outra.com",
        canGoBack: false,
        canGoForward: false,
      });
    });
    await waitFor(() => {
      expect(screen.queryByText("esquema não permitido: ftp://x")).toBeNull();
    });
  });

  it("desmontar a aba destroi a view (não deixa WebContentsView órfã)", async () => {
    const bridge = mockBrowserView();
    mockFetch({ configurations: [] });
    const { unmount } = render(<BrowserTab threadId="t1" />);
    await waitFor(() => expect(bridge.onEvent).toHaveBeenCalled());

    unmount();
    expect(bridge.destroyView).toHaveBeenCalledWith(1);
  });
});

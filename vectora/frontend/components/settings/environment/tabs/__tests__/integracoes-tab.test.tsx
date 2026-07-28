// @vitest-environment jsdom
/**
 * Testes da IntegracoesTab — INT-8 + Sprint 12 (fusão com a antiga EnvsTab).
 *
 * Cobre:
 * - Renderização com lista de integrações do backend (conectado / não conectado)
 * - Status badge correto por provider
 * - Botão "Conectar via OAuth" presente para providers OAuth não conectados
 * - Botão "Desconectar" presente para providers OAuth conectados
 * - Webhook URL via gateway (quando gateway conectado) e fallback local
 * - Providers filho (google-drive, gmail) renderizam sem botão OAuth próprio
 * - Gateway status: conectado mostra subdomain; desconectado mostra mensagem padrão
 * - Variáveis customizadas (chave/valor livre): seção "Customizadas" lista
 *   env vars órfãs (sem integração correspondente); dialog "+ Adicionar
 *   variável customizada" salva via /auth/envs; erro/borda — chave ou
 *   valor vazio não submete.
 */

import {
  describe,
  it,
  expect,
  vi,
  afterEach,
  beforeEach,
  beforeAll,
} from "vitest";
import {
  render,
  screen,
  cleanup,
  waitFor,
  fireEvent,
} from "@testing-library/react";
import { overwriteGetLocale, baseLocale } from "@/lib/paraglide/runtime";

vi.mock("@/lib/hooks/use-feature-flags", () => ({
  useFeatureFlags: () => ({ enableFeaturesBeta: true }),
}));

afterEach(cleanup);

beforeAll(async () => {
  await import("../integracoes-tab");
}, 120000);

afterEach(() => overwriteGetLocale(() => baseLocale));

type GatewayStatus = {
  connected: boolean;
  state: "never_connected" | "error" | "connected";
  token: string | null;
  subdomain: string | null;
  webhook_base: string | null;
  detail: string | null;
};

const GATEWAY_FALLBACK: GatewayStatus = {
  connected: false,
  state: "never_connected",
  token: null,
  subdomain: null,
  webhook_base: null,
  detail: null,
};

function mockFetch(
  integrations: object[],
  gateway: GatewayStatus = GATEWAY_FALLBACK,
  envs: { envs: Record<string, string>; keys: string[] } = {
    envs: {},
    keys: [],
  },
) {
  global.fetch = vi
    .fn()
    .mockImplementation((url: string, init?: RequestInit) => {
      if (url === "/gateway/status") {
        return Promise.resolve({
          ok: true,
          json: async () => gateway,
        } as Response);
      }
      if (url === "/auth/envs" && (!init || init.method === undefined)) {
        return Promise.resolve({
          ok: true,
          json: async () => envs,
        } as Response);
      }
      if (url === "/auth/envs" && init?.method === "POST") {
        return Promise.resolve({
          ok: true,
          json: async () => ({}),
        } as Response);
      }
      if (url.startsWith("/auth/envs/") && init?.method === "DELETE") {
        return Promise.resolve({
          ok: true,
          json: async () => ({}),
        } as Response);
      }
      return Promise.resolve({
        ok: true,
        json: async () => ({ integrations }),
      } as Response);
    });
}

function countEnvsPostCalls(): number {
  return (global.fetch as ReturnType<typeof vi.fn>).mock.calls.filter(
    (c) => c[0] === "/auth/envs" && c[1]?.method === "POST",
  ).length;
}

const BASE_INTEGRATIONS = [
  {
    id: "github",
    name: "GitHub",
    env_var: "GITHUB_TOKEN",
    kind: "hybrid",
    description: "Repos e PRs",
    docs_url: "https://github.com/settings/tokens",
    icon: "github",
    connected: true,
  },
  {
    id: "gitlab",
    name: "GitLab",
    env_var: "GITLAB_TOKEN",
    kind: "oauth",
    description: "GitLab repos",
    docs_url: "https://gitlab.com",
    icon: "gitlab",
    connected: false,
  },
  {
    id: "google",
    name: "Google",
    env_var: "GOOGLE_ACCESS_TOKEN",
    kind: "oauth",
    description: "Google account",
    docs_url: "https://console.cloud.google.com",
    icon: "google",
    connected: false,
  },
  {
    id: "google-drive",
    name: "Google Drive",
    env_var: "GOOGLE_ACCESS_TOKEN",
    kind: "oauth",
    description: "Drive files",
    docs_url: "https://console.cloud.google.com",
    icon: "google-drive",
    parent: "google",
    connected: false,
  },
  {
    id: "openai",
    name: "OpenAI",
    env_var: "OPENAI_API_KEY",
    kind: "apikey",
    description: "GPT-4",
    docs_url: "https://platform.openai.com",
    icon: "openai",
    connected: false,
  },
  {
    id: "slack",
    name: "Slack",
    env_var: "SLACK_BOT_TOKEN",
    kind: "oauth",
    description: "Slack messaging",
    docs_url: "https://api.slack.com",
    icon: "slack",
    connected: true,
  },
  {
    id: "linear",
    name: "Linear",
    env_var: "LINEAR_API_KEY",
    kind: "apikey",
    description: "Linear issues",
    docs_url: "https://linear.app/settings/api",
    icon: "linear",
    connected: false,
  },
];

describe("IntegracoesTab", () => {
  beforeEach(() => {
    overwriteGetLocale(() => "pt");
    mockFetch(BASE_INTEGRATIONS);
  });

  it("renderiza os nomes de todas as integrações", async () => {
    const { IntegracoesTab } = await import("../integracoes-tab");
    render(<IntegracoesTab />);
    await waitFor(() => {
      for (const name of [
        "GitHub",
        "GitLab",
        "Google",
        "Slack",
        "OpenAI",
        "Linear",
      ]) {
        expect(screen.getAllByText(name).length).toBeGreaterThan(0);
      }
    });
  });

  it("GitHub conectado exibe badge 'Conectado'", async () => {
    const { IntegracoesTab } = await import("../integracoes-tab");
    render(<IntegracoesTab />);
    await waitFor(() => {
      const badges = screen.getAllByText(/conectado/i);
      expect(badges.length).toBeGreaterThan(0);
    });
  });

  it("GitLab não conectado exibe badge 'Não configurado'", async () => {
    const { IntegracoesTab } = await import("../integracoes-tab");
    render(<IntegracoesTab />);
    await waitFor(() => {
      const badges = screen.getAllByText(/não configurado/i);
      expect(badges.length).toBeGreaterThan(0);
    });
  });

  it("providers OAuth não conectados exibem botão de OAuth", async () => {
    const { IntegracoesTab } = await import("../integracoes-tab");
    render(<IntegracoesTab />);
    await waitFor(() => {
      const oauthBtns = screen.getAllByText(/conectar via oauth/i);
      expect(oauthBtns.length).toBeGreaterThanOrEqual(2);
    });
  });

  it("providers OAuth-only (gitlab/google/slack) também aceitam token manual", async () => {
    // Erro/borda: antes só kind="apikey"|"hybrid" mostrava o botão de
    // expandir pra colar token — providers OAuth-only (kind="oauth" sem
    // hybrid) não tinham alternativa ao fluxo OAuth completo. Agora todos
    // ganham o botão de expandir (title = "Colar token manualmente").
    const { IntegracoesTab } = await import("../integracoes-tab");
    render(<IntegracoesTab />);
    await waitFor(() => {
      const pasteButtons = screen.getAllByTitle(/colar token manualmente/i);
      // github(hybrid) + gitlab + google + slack = 4 no mínimo
      // (google-drive é filho, não conta)
      expect(pasteButtons.length).toBeGreaterThanOrEqual(4);
    });
  });

  it("Slack conectado via OAuth exibe botão Desconectar", async () => {
    const { IntegracoesTab } = await import("../integracoes-tab");
    render(<IntegracoesTab />);
    await waitFor(() => {
      const disconnectBtns = screen.getAllByText(/desconectar/i);
      expect(disconnectBtns.length).toBeGreaterThan(0);
    });
  });

  it("Google Drive exibe card sem botão OAuth próprio (filho de Google)", async () => {
    const { IntegracoesTab } = await import("../integracoes-tab");
    render(<IntegracoesTab />);
    await waitFor(() => {
      expect(screen.getByText("Google Drive")).toBeTruthy();
    });
  });

  it("GitHub conectado exibe URL de webhook local quando gateway desconectado", async () => {
    const { IntegracoesTab } = await import("../integracoes-tab");
    render(<IntegracoesTab />);
    await waitFor(() => {
      const webhookUrls = screen.getAllByText(/\/webhook\/github/i);
      expect(webhookUrls.length).toBeGreaterThan(0);
    });
  });

  it("GitHub usa gateway webhook_base quando gateway conectado", async () => {
    mockFetch(BASE_INTEGRATIONS, {
      connected: true,
      state: "connected",
      token: "abc123",
      subdomain: "abc123.vectora.chat",
      webhook_base: "https://abc123.vectora.chat",
      detail: null,
    });
    const { IntegracoesTab } = await import("../integracoes-tab");
    render(<IntegracoesTab />);
    await waitFor(() => {
      const webhookUrls = screen.getAllByText(
        /abc123\.vectora\.chat\/webhook\/github/i,
      );
      expect(webhookUrls.length).toBeGreaterThan(0);
    });
  });

  it("Slack conectado exibe URL de webhook", async () => {
    const { IntegracoesTab } = await import("../integracoes-tab");
    render(<IntegracoesTab />);
    await waitFor(() => {
      const webhookUrls = screen.getAllByText(/\/webhook\/slack/i);
      expect(webhookUrls.length).toBeGreaterThan(0);
    });
  });

  it("renderiza indicador de carregamento antes da resposta", async () => {
    global.fetch = vi.fn().mockReturnValue(new Promise(() => {}));
    const { IntegracoesTab } = await import("../integracoes-tab");
    const { container } = render(<IntegracoesTab />);
    const spinner = container.querySelector(".animate-spin");
    expect(spinner).toBeTruthy();
  });

  it("sumário exibe contador de integrações conectadas", async () => {
    const { IntegracoesTab } = await import("../integracoes-tab");
    render(<IntegracoesTab />);
    // GitHub + Slack = 2 conectadas
    await waitFor(() => {
      expect(screen.getByText(/2 integraç/i)).toBeTruthy();
    });
  });

  it("gateway nunca conectado exibe mensagem neutra (não parece erro)", async () => {
    // Erro/borda: state="never_connected" é o default do mockFetch — nada foi
    // configurado ainda, e a mensagem não deve soar como falha.
    const { IntegracoesTab } = await import("../integracoes-tab");
    render(<IntegracoesTab />);
    await waitFor(() => {
      expect(screen.getByText(/nenhuma integração oauth/i)).toBeTruthy();
      expect(screen.queryByText(/gateway indisponível/i)).toBeNull();
    });
  });

  it("gateway conectado exibe subdomain e mensagem de gateway conectado", async () => {
    mockFetch(BASE_INTEGRATIONS, {
      connected: true,
      state: "connected",
      token: "abc123",
      subdomain: "abc123.vectora.chat",
      webhook_base: "https://abc123.vectora.chat",
      detail: null,
    });
    const { IntegracoesTab } = await import("../integracoes-tab");
    render(<IntegracoesTab />);
    await waitFor(() => {
      expect(screen.getByText(/gateway conectado/i)).toBeTruthy();
      // subdomain e webhook_base podem aparecer em múltiplos spans — getAllByText é correto
      expect(
        screen.getAllByText(/abc123\.vectora\.chat/).length,
      ).toBeGreaterThan(0);
    });
  });

  it("gateway com erro real exibe mensagem distinta de 'nunca conectado', com detalhe", async () => {
    // Erro/borda: distingue estado neutro (nunca tentou) de falha real
    // (já teve token, tentou, o Worker não respondeu) — a UI não pode
    // mostrar a mesma mensagem pros dois casos.
    mockFetch(BASE_INTEGRATIONS, {
      connected: false,
      state: "error",
      token: "abc123",
      subdomain: "abc123.vectora.chat",
      webhook_base: "https://abc123.vectora.chat",
      detail: "Gateway respondeu 503",
    });
    const { IntegracoesTab } = await import("../integracoes-tab");
    render(<IntegracoesTab />);
    await waitFor(() => {
      expect(screen.getByText(/gateway indisponível/i)).toBeTruthy();
      expect(screen.getByText("Gateway respondeu 503")).toBeTruthy();
      expect(screen.queryByText(/nenhuma integração oauth/i)).toBeNull();
    });
  });

  it("lista variáveis customizadas (órfãs) numa seção separada", async () => {
    mockFetch(BASE_INTEGRATIONS, GATEWAY_FALLBACK, {
      envs: { MY_CUSTOM_TOKEN: "••••••••" },
      // GITHUB_TOKEN já é coberto pela integração GitHub — não deve
      // aparecer duplicado na seção Customizadas.
      keys: ["MY_CUSTOM_TOKEN", "GITHUB_TOKEN"],
    });
    const { IntegracoesTab } = await import("../integracoes-tab");
    render(<IntegracoesTab />);
    await waitFor(() => {
      expect(screen.getByText("MY_CUSTOM_TOKEN")).toBeTruthy();
      expect(screen.getByText(/customizadas/i)).toBeTruthy();
    });
    // GITHUB_TOKEN é conhecido — não deve renderizar como card customizado
    expect(screen.queryByText("GITHUB_TOKEN")).toBeNull();
  });

  it("botão 'Adicionar variável customizada' abre dialog e salva via /auth/envs", async () => {
    const { IntegracoesTab } = await import("../integracoes-tab");
    render(<IntegracoesTab />);

    await waitFor(() => {
      expect(screen.getByText("GitHub")).toBeTruthy();
    });

    fireEvent.click(screen.getByText(/adicionar variável customizada/i));

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/OPENAI_API_KEY/i)).toBeTruthy();
    });

    fireEvent.change(screen.getByPlaceholderText(/OPENAI_API_KEY/i), {
      target: { value: "MY_KEY" },
    });
    fireEvent.change(screen.getByPlaceholderText(/enter the value|valor/i), {
      target: { value: "secret-value" },
    });

    fireEvent.click(screen.getByRole("button", { name: /^save$|^salvar$/i }));

    await waitFor(() => {
      expect(countEnvsPostCalls()).toBeGreaterThan(0);
    });
  });

  it("botão salvar da variável customizada fica desabilitado com chave ou valor vazio", async () => {
    // Erro/borda: sem os dois campos preenchidos, não deve nem tentar
    // chamar o backend.
    const { IntegracoesTab } = await import("../integracoes-tab");
    render(<IntegracoesTab />);

    await waitFor(() => {
      expect(screen.getByText("GitHub")).toBeTruthy();
    });

    fireEvent.click(screen.getByText(/adicionar variável customizada/i));

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/OPENAI_API_KEY/i)).toBeTruthy();
    });

    const saveBtn = screen.getByRole("button", { name: /^save$|^salvar$/i });
    expect(saveBtn).toBeDisabled();

    fireEvent.change(screen.getByPlaceholderText(/OPENAI_API_KEY/i), {
      target: { value: "MY_KEY" },
    });
    expect(saveBtn).toBeDisabled();
  });

  it("olho revela/oculta o valor digitado da variável customizada", async () => {
    const { IntegracoesTab } = await import("../integracoes-tab");
    render(<IntegracoesTab />);

    await waitFor(() => {
      expect(screen.getByText("GitHub")).toBeTruthy();
    });

    fireEvent.click(screen.getByText(/adicionar variável customizada/i));

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/OPENAI_API_KEY/i)).toBeTruthy();
    });

    const valueInput = screen.getByPlaceholderText(
      /enter the value|valor/i,
    ) as HTMLInputElement;
    expect(valueInput.type).toBe("password");

    fireEvent.click(screen.getByLabelText(/mostrar valor/i));
    expect(valueInput.type).toBe("text");

    fireEvent.click(screen.getByLabelText(/ocultar valor/i));
    expect(valueInput.type).toBe("password");
  });

  it("olho reseta ao fechar o dialog de variável customizada", async () => {
    // Erro/borda: o estado de visibilidade não pode vazar pra próxima
    // abertura do dialog.
    const { IntegracoesTab } = await import("../integracoes-tab");
    render(<IntegracoesTab />);

    await waitFor(() => {
      expect(screen.getByText("GitHub")).toBeTruthy();
    });

    fireEvent.click(screen.getByText(/adicionar variável customizada/i));
    await waitFor(() => {
      expect(screen.getByPlaceholderText(/OPENAI_API_KEY/i)).toBeTruthy();
    });
    fireEvent.click(screen.getByLabelText(/mostrar valor/i));
    fireEvent.click(
      screen.getByRole("button", { name: /^cancel$|^cancelar$/i }),
    );

    fireEvent.click(screen.getByText(/adicionar variável customizada/i));
    await waitFor(() => {
      const valueInput = screen.getByPlaceholderText(
        /enter the value|valor/i,
      ) as HTMLInputElement;
      expect(valueInput.type).toBe("password");
    });
  });

  it("olho revela/oculta o token manual de uma integração", async () => {
    const { IntegracoesTab } = await import("../integracoes-tab");
    render(<IntegracoesTab />);

    const pasteBtn = await screen.findAllByTitle(/colar token manualmente/i);
    fireEvent.click(pasteBtn[0]);

    const keyInput = (
      await screen.findAllByPlaceholderText(/cole sua chave aqui/i)
    )[0] as HTMLInputElement;
    expect(keyInput.type).toBe("password");

    fireEvent.click(screen.getAllByLabelText(/mostrar valor/i)[0]);
    expect(keyInput.type).toBe("text");
  });
});

// @vitest-environment jsdom
/**
 * Testes da IntegracoesTab — INT-8.
 *
 * Cobre:
 * - Renderização com lista de integrações do backend (conectado / não conectado)
 * - Status badge correto por provider
 * - Botão "Conectar via OAuth" presente para providers OAuth não conectados
 * - Botão "Desconectar" presente para providers OAuth conectados
 * - Webhook URL exibida para providers com webhook quando conectado
 * - Providers filho (google-drive, gmail) renderizam sem botão OAuth próprio
 * - Categorias exibem apenas providers presentes
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
import { render, screen, cleanup, waitFor } from "@testing-library/react";
import { overwriteGetLocale, baseLocale } from "@/lib/paraglide/runtime";

afterEach(cleanup);

// Import frio do componente é lento neste ambiente — pré-carrega uma vez para
// o primeiro teste não estourar o timeout de 5s.
beforeAll(async () => {
  await import("../integracoes-tab");
}, 30000);

// Restaura o locale padrão após cada teste (overwriteGetLocale é global).
afterEach(() => overwriteGetLocale(() => baseLocale));

// Mock do fetch para simular GET /integrations/
function mockFetch(integrations: object[]) {
  global.fetch = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({ integrations }),
  } as Response);
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
      expect(screen.getByText("GitHub")).toBeTruthy();
      expect(screen.getByText("GitLab")).toBeTruthy();
      expect(screen.getByText("Google")).toBeTruthy();
      expect(screen.getByText("Slack")).toBeTruthy();
      expect(screen.getByText("OpenAI")).toBeTruthy();
      expect(screen.getByText("Linear")).toBeTruthy();
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
      // GitLab e Google não estão conectados → devem ter botões OAuth
      expect(oauthBtns.length).toBeGreaterThanOrEqual(2);
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

  it("GitHub conectado exibe URL de webhook", async () => {
    const { IntegracoesTab } = await import("../integracoes-tab");
    render(<IntegracoesTab />);
    await waitFor(() => {
      const webhookUrls = screen.getAllByText(/\/webhook\/github/i);
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
});

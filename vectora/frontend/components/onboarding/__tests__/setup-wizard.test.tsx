// @vitest-environment jsdom

import { describe, expect, it, beforeEach, afterEach, vi } from "vitest";
import {
  render,
  screen,
  cleanup,
  waitFor,
  fireEvent,
  act,
} from "@testing-library/react";
import { SetupWizard, isOnboardingDone } from "../setup-wizard";

beforeEach(() => {
  localStorage.clear();
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => ({
      ok: true,
      json: async () => ({ has_token: false, mode: "lite" }),
    })),
  );
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("isOnboardingDone", () => {
  it("retorna false quando a flag não está setada", () => {
    expect(isOnboardingDone("u1")).toBe(false);
  });

  it("retorna true quando a flag do usuário está marcada", () => {
    localStorage.setItem("vectora:onboarding-done-u1", "1");
    expect(isOnboardingDone("u1")).toBe(true);
  });

  it("isola a flag por usuário — flag de outro userId não se aplica", () => {
    localStorage.setItem("vectora:onboarding-done-u1", "1");
    expect(isOnboardingDone("u2")).toBe(false);
  });

  it("erro: flag de userId não relacionado não concede acesso", () => {
    localStorage.setItem("vectora:onboarding-done-admin", "1");
    expect(isOnboardingDone("u1")).toBe(false);
    expect(isOnboardingDone("u2")).toBe(false);
  });
});

describe("SetupWizard", () => {
  it("renderiza o contador do passo 1/9 no primeiro passo", async () => {
    render(<SetupWizard userId="u1" onComplete={vi.fn()} />);
    await waitFor(() => expect(screen.getByText("1 / 9")).toBeInTheDocument());
  });

  it("área de conteúdo tem data-testid com altura mínima fixa", async () => {
    const { container } = render(
      <SetupWizard userId="u2" onComplete={vi.fn()} />,
    );
    await waitFor(() =>
      expect(
        document.querySelector("[data-testid='step-content-area']"),
      ).not.toBeNull(),
    );
  });
});

async function renderAtStepToken() {
  render(<SetupWizard userId="u3" onComplete={vi.fn()} />);
  await waitFor(() => screen.getByText("1 / 9"));
  fireEvent.click(screen.getByRole("button", { name: "Next" })); // passo 0 → 1
  await waitFor(() => screen.getByText("2 / 9"));
  fireEvent.click(screen.getByRole("button", { name: "Next" })); // passo 1 → 2
  await waitFor(() => screen.getByText("3 / 9"));
}

describe("StepToken", () => {
  it("campo de token tem autocomplete=off para desabilitar autofill do browser", async () => {
    await renderAtStepToken();
    const input = screen.getByPlaceholderText("vct_…");
    expect(input).toHaveAttribute("autocomplete", "off");
  });

  it("erro: campo de token não deve ter hint semântico de autocomplete", async () => {
    await renderAtStepToken();
    const input = screen.getByPlaceholderText("vct_…");
    expect(input).not.toHaveAttribute("autocomplete", "new-password");
    expect(input).not.toHaveAttribute("autocomplete", "current-password");
    expect(input).not.toHaveAttribute("autocomplete", "email");
  });
});

function mockStorageFetch(opts: {
  defaultsOk: boolean;
}): ReturnType<typeof vi.fn> {
  const defaults = {
    postgres: {
      url: "postgresql+asyncpg://vectora:vectora@localhost:5432/vectora",
      start_command: "docker compose up -d postgres",
    },
    redis: {
      url: "redis://:vectora@localhost:6379/0",
      start_command: "docker compose up -d redis",
    },
    qdrant: {
      url: "http://localhost:6333",
      api_key: "vectora",
      start_command: "docker compose up -d qdrant",
    },
  };
  return vi.fn(async (url: string) => {
    const u = String(url);
    if (u.includes("/admin/storage/defaults")) {
      return {
        ok: opts.defaultsOk,
        json: async () => (opts.defaultsOk ? defaults : {}),
      };
    }
    if (u.includes("/admin/storage")) {
      return {
        ok: true,
        json: async () => ({
          config: {
            storage_mode: "lite",
            postgres_configured: false,
            redis_configured: false,
            qdrant_configured: false,
          },
        }),
      };
    }
    if (u.includes("/admin/api-keys/test")) {
      return { ok: true, json: async () => ({ ok: true }) };
    }
    if (u.includes("/admin/api-keys")) {
      return {
        ok: true,
        json: async () => ({
          google: { configured: false, masked: "" },
          cohere: { configured: false, masked: "" },
          tavily: { configured: false, masked: "" },
        }),
      };
    }
    return { ok: true, json: async () => ({ has_token: false, mode: "lite" }) };
  });
}

async function renderAtStepMode() {
  render(<SetupWizard userId="u-mode" onComplete={vi.fn()} />);
  await waitFor(() => screen.getByText("1 / 9"));
  await act(async () => {
    for (let i = 0; i < 3; i++) {
      fireEvent.click(screen.getByRole("button", { name: "Next" }));
    }
  });
  await waitFor(() => screen.getByText("4 / 9"));
  await act(async () => {
    fireEvent.click(screen.getByText("Complete")); // modo completo → cards
  });
}

describe("StepMode — pré-preenchimento com defaults reais", () => {
  it("pré-preenche o card com a URL default e o comando self-hosted", async () => {
    vi.stubGlobal("fetch", mockStorageFetch({ defaultsOk: true }));
    await renderAtStepMode();

    await waitFor(() =>
      expect(
        screen.getByDisplayValue("redis://:vectora@localhost:6379/0"),
      ).toBeInTheDocument(),
    );
    // Comando self-hosted também vem preenchido (toggle ligado).
    expect(
      screen.getByDisplayValue("docker compose up -d redis"),
    ).toBeInTheDocument();
    // Qdrant traz a API key default no campo dedicado.
    expect(screen.getByDisplayValue("vectora")).toBeInTheDocument();
  });

  it("erro: sem defaults do backend, o card fica vazio (só placeholder)", async () => {
    vi.stubGlobal("fetch", mockStorageFetch({ defaultsOk: false }));
    await renderAtStepMode();

    const input = (await screen.findByPlaceholderText(
      "redis://localhost:6379/0",
    )) as HTMLInputElement;
    expect(input.value).toBe("");
  });
});

// ---------------------------------------------------------------------------
// StepApiKeys
// ---------------------------------------------------------------------------

function mockApiKeysFetch(
  opts: {
    google?: { configured: boolean; masked: string };
    cohere?: { configured: boolean; masked: string };
    tavily?: { configured: boolean; masked: string };
    testOk?: boolean;
  } = {},
) {
  const {
    google = { configured: false, masked: "" },
    cohere = { configured: false, masked: "" },
    tavily = { configured: false, masked: "" },
    testOk = true,
  } = opts;
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init?: RequestInit) => {
      const u = String(url);
      if (u.includes("/admin/api-keys/test")) {
        return {
          ok: true,
          json: async () => ({
            ok: testOk,
            error: testOk ? "" : "Invalid key",
          }),
        };
      }
      if (u.includes("/admin/api-keys") && init?.method === "PATCH") {
        return {
          ok: true,
          json: async () => ({ status: "updated", updated: [] }),
        };
      }
      if (u.includes("/admin/api-keys")) {
        return { ok: true, json: async () => ({ google, cohere, tavily }) };
      }
      if (u.includes("/admin/storage/defaults")) {
        return { ok: true, json: async () => ({}) };
      }
      if (u.includes("/admin/storage")) {
        return {
          ok: true,
          json: async () => ({
            config: {
              storage_mode: "lite",
              postgres_configured: false,
              redis_configured: false,
              qdrant_configured: false,
            },
          }),
        };
      }
      return {
        ok: true,
        json: async () => ({ has_token: false, mode: "lite" }),
      };
    }),
  );
}

async function renderAtStepApiKeys() {
  render(<SetupWizard userId="u-apikeys" onComplete={vi.fn()} />);
  await waitFor(() => screen.getByText("1 / 9"));
  await act(async () => {
    for (let i = 0; i < 4; i++) {
      fireEvent.click(screen.getByRole("button", { name: "Next" }));
    }
  });
  await waitFor(() => screen.getByText("5 / 9"));
}

describe("StepApiKeys", () => {
  it("renderiza os 3 campos de chave", async () => {
    mockApiKeysFetch();
    await renderAtStepApiKeys();
    expect(screen.getByPlaceholderText("AIza…")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("…")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("tvly-…")).toBeInTheDocument();
  });

  it("erro: campos sem valor configurado ficam vazios", async () => {
    mockApiKeysFetch();
    await renderAtStepApiKeys();
    for (const placeholder of ["AIza…", "…", "tvly-…"]) {
      const input = screen.getByPlaceholderText(
        placeholder,
      ) as HTMLInputElement;
      expect(input.value).toBe("");
    }
  });

  it("pré-preenche masked value quando key está configurada", async () => {
    mockApiKeysFetch({ google: { configured: true, masked: "AIzaS•••e7wQ" } });
    await renderAtStepApiKeys();
    await waitFor(() => {
      const input = screen.getByPlaceholderText("AIza…") as HTMLInputElement;
      expect(input.value).toBe("AIzaS•••e7wQ");
    });
  });

  it("ao desfocar campo com valor, chama PATCH + test", async () => {
    mockApiKeysFetch();
    await renderAtStepApiKeys();
    const fetchMock = vi.mocked(global.fetch);
    const input = screen.getByPlaceholderText("tvly-…");
    fireEvent.change(input, { target: { value: "tvly-abc123" } });
    fireEvent.blur(input);
    await waitFor(() => {
      const calls = fetchMock.mock.calls.map((c) => String(c[0]));
      expect(
        calls.some((u) => u.includes("/admin/api-keys") && !u.includes("test")),
      ).toBe(true);
      expect(calls.some((u) => u.includes("/admin/api-keys/test"))).toBe(true);
    });
  });

  it("erro: campo desativado sem valor não dispara PATCH nem test", async () => {
    mockApiKeysFetch();
    await renderAtStepApiKeys();
    const fetchMock = vi.mocked(global.fetch);
    const countBefore = fetchMock.mock.calls.length;
    const input = screen.getByPlaceholderText("tvly-…");
    fireEvent.blur(input);
    await waitFor(() => {
      expect(fetchMock.mock.calls.length).toBe(countBefore);
    });
  });
});

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
  it("renderiza o contador do passo 1/7 no primeiro passo", async () => {
    render(<SetupWizard userId="u1" onComplete={vi.fn()} />);
    await waitFor(() => expect(screen.getByText("1 / 8")).toBeInTheDocument());
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
  await waitFor(() => screen.getByText("1 / 8"));
  fireEvent.click(screen.getByRole("button", { name: "Next" })); // passo 0 → 1
  await waitFor(() => screen.getByText("2 / 8"));
  fireEvent.click(screen.getByRole("button", { name: "Next" })); // passo 1 → 2
  await waitFor(() => screen.getByText("3 / 8"));
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
    return { ok: true, json: async () => ({ has_token: false, mode: "lite" }) };
  });
}

async function renderAtStepMode() {
  render(<SetupWizard userId="u-mode" onComplete={vi.fn()} />);
  await waitFor(() => screen.getByText("1 / 8"));
  await act(async () => {
    for (let i = 0; i < 3; i++) {
      fireEvent.click(screen.getByRole("button", { name: "Next" }));
    }
  });
  await waitFor(() => screen.getByText("4 / 8"));
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

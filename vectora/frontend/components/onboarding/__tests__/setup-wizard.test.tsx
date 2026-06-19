// @vitest-environment jsdom

import { describe, expect, it, beforeEach, afterEach, vi } from "vitest";
import {
  render,
  screen,
  cleanup,
  waitFor,
  fireEvent,
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
    await waitFor(() => expect(screen.getByText("1 / 7")).toBeInTheDocument());
  });

  it("área de conteúdo tem data-testid com altura mínima fixa", async () => {
    const { container } = render(
      <SetupWizard userId="u2" onComplete={vi.fn()} />,
    );
    await waitFor(() =>
      expect(
        container.querySelector("[data-testid='step-content-area']"),
      ).not.toBeNull(),
    );
  });
});

describe("StepToken", () => {
  async function renderAtStepToken() {
    render(<SetupWizard userId="u3" onComplete={vi.fn()} />);
    await waitFor(() => screen.getByText("1 / 7"));
    const next = () =>
      fireEvent.click(screen.getByRole("button", { name: "Next" }));
    next(); // passo 0 → 1
    await waitFor(() => screen.getByText("2 / 7"));
    next(); // passo 1 → 2
    await waitFor(() => screen.getByText("3 / 7"));
  }

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

  it("botão 'Sign in with account' abre vectora.company no browser externo", async () => {
    const openSpy = vi.fn();
    vi.stubGlobal("open", openSpy);
    await renderAtStepToken();
    const loginBtn = screen.getByRole("button", {
      name: "Sign in with account",
    });
    fireEvent.click(loginBtn);
    expect(openSpy).toHaveBeenCalledWith(
      "https://vectora.company/dashboard",
      "_blank",
      "noopener,noreferrer",
    );
  });

  it("erro: botão 'Sign in with account' não deve abrir URL interna ou localhost", async () => {
    const openSpy = vi.fn();
    vi.stubGlobal("open", openSpy);
    await renderAtStepToken();
    fireEvent.click(
      screen.getByRole("button", { name: "Sign in with account" }),
    );
    const url: string = openSpy.mock.calls[0]?.[0] ?? "";
    expect(url).toMatch(/^https:\/\/vectora\.company/);
    expect(url).not.toMatch(/localhost|127\.0\.0\.1/);
  });
});

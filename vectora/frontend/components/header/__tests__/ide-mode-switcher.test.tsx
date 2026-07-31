// @vitest-environment jsdom
/**
 * O 3º modo é dev-only: fora de `VECTORA_DEV=1` o usuário não vê a opção
 * existir — diferente de vê-la desabilitada, que sugeriria "compre o Pro".
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, render, screen } from "@testing-library/react";

import { overwriteGetLocale, baseLocale } from "@/lib/paraglide/runtime";
import { useSettingsStore } from "@/lib/stores/settings-store";

const { useFeatureFlagsMock, useElementWidthMock } = vi.hoisted(() => ({
  useFeatureFlagsMock: vi.fn(),
  useElementWidthMock: vi.fn(),
}));

vi.mock("@/lib/hooks/use-feature-flags", () => ({
  useFeatureFlags: useFeatureFlagsMock,
}));

vi.mock("@/lib/hooks/use-element-width", () => ({
  useElementWidth: useElementWidthMock,
}));

const { IdeModeSwitch } = await import("../ide-mode-switcher");

beforeEach(() => {
  overwriteGetLocale(() => "pt");
  useElementWidthMock.mockReturnValue([{ current: null }, 300]);
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  overwriteGetLocale(() => baseLocale);
});

async function montar(enableKanbanMode: boolean, width = 300) {
  useFeatureFlagsMock.mockReturnValue({
    enableFeaturesBeta: true,
    enableKanbanMode,
  });
  useElementWidthMock.mockReturnValue([{ current: null }, width]);
  render(<IdeModeSwitch show />);
  await act(async () => {});
}

describe("IdeModeSwitch — 3ª posição", () => {
  it("com a flag ligada mostra Kanban", async () => {
    await montar(true);
    expect(screen.getByRole("button", { name: /kanban/i })).toBeInTheDocument();
  });

  it("com a flag desligada o seletor continua binário", async () => {
    // Erro/borda central: o usuário comum não vê a opção, não a vê inerte.
    await montar(false);

    expect(
      screen.queryByRole("button", { name: /kanban/i }),
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /assistente/i }),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /ide/i })).toBeInTheDocument();
  });

  it("show=false esconde o seletor inteiro", async () => {
    useFeatureFlagsMock.mockReturnValue({
      enableFeaturesBeta: true,
      enableKanbanMode: true,
    });
    render(<IdeModeSwitch show={false} />);
    await act(async () => {});

    expect(screen.queryByRole("group")).not.toBeInTheDocument();
  });
});

describe("IdeModeSwitch — colapso responsivo", () => {
  it("largura grande mostra o texto completo, visível (sem sr-only)", async () => {
    await montar(true, 300);
    const botao = screen.getByRole("button", { name: /assistente/i });
    const label = botao.querySelector("span");
    expect(label?.className).not.toContain("sr-only");
    expect(label?.className).not.toContain("truncate");
  });

  it("largura média trunca o texto (classe truncate), mas mantém visível", async () => {
    await montar(true, 200);
    const botao = screen.getByRole("button", { name: /assistente/i });
    const label = botao.querySelector("span");
    expect(label?.className).toContain("truncate");
    expect(label?.className).not.toContain("sr-only");
  });

  it("largura pequena esconde o texto (sr-only) mas mantém o nome acessível", async () => {
    await montar(true, 100);
    const botao = screen.getByRole("button", { name: /assistente/i });
    const label = botao.querySelector("span");
    expect(label?.className).toContain("sr-only");
    // O botão continua com nome acessível pra leitor de tela — não sumiu,
    // só ficou visualmente oculto.
    expect(botao).toBeInTheDocument();
  });
});

describe("IdeModeSwitch — cor por modo ativo", () => {
  afterEach(async () => {
    await act(async () => {
      useSettingsStore.getState().setUiMode("ide");
    });
  });

  it("modo kanban ativo ganha classe âmbar", async () => {
    useSettingsStore.getState().setUiMode("kanban");
    await montar(true);
    const botao = screen.getByRole("button", { name: /kanban/i });
    expect(botao.className).toContain("amber");
  });

  it("modo assistente ativo ganha classe azul", async () => {
    useSettingsStore.getState().setUiMode("assistant");
    await montar(true);
    const botao = screen.getByRole("button", { name: /assistente/i });
    expect(botao.className).toContain("blue");
  });

  it("modo inativo permanece neutro, sem cor de destaque", async () => {
    useSettingsStore.getState().setUiMode("kanban");
    await montar(true);
    const botao = screen.getByRole("button", { name: /ide/i });
    expect(botao.className).not.toContain("amber");
    expect(botao.className).not.toContain("blue");
    expect(botao.className).not.toContain("violet");
  });
});

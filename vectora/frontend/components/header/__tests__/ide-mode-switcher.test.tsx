// @vitest-environment jsdom
/**
 * O 3º modo é dev-only: fora de `VECTORA_DEV=1` o usuário não vê a opção
 * existir — diferente de vê-la desabilitada, que sugeriria "compre o Pro".
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, render, screen } from "@testing-library/react";

import { overwriteGetLocale, baseLocale } from "@/lib/paraglide/runtime";

const { useFeatureFlagsMock } = vi.hoisted(() => ({
  useFeatureFlagsMock: vi.fn(),
}));

vi.mock("@/lib/hooks/use-feature-flags", () => ({
  useFeatureFlags: useFeatureFlagsMock,
}));

const { IdeModeSwitch } = await import("../ide-mode-switcher");

beforeEach(() => overwriteGetLocale(() => "pt"));
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  overwriteGetLocale(() => baseLocale);
});

async function montar(enableKanbanMode: boolean) {
  useFeatureFlagsMock.mockReturnValue({
    enableFeaturesBeta: true,
    enableKanbanMode,
  });
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

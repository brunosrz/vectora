// @vitest-environment jsdom
/**
 * Tests para o SetupWizard: flag isOnboardingDone (localStorage) e smoke
 * render do passo 1/7.
 */

import { describe, expect, it, beforeEach, afterEach, vi } from "vitest";
import { render, screen, cleanup, waitFor } from "@testing-library/react";
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
  it("false quando a flag não está setada", () => {
    expect(isOnboardingDone("u1")).toBe(false);
  });

  it("true quando a flag do usuário está marcada", () => {
    localStorage.setItem("vectora:onboarding-done-u1", "1");
    expect(isOnboardingDone("u1")).toBe(true);
  });

  it("isola a flag por usuário", () => {
    localStorage.setItem("vectora:onboarding-done-u1", "1");
    expect(isOnboardingDone("u2")).toBe(false);
  });
});

describe("SetupWizard", () => {
  it("renderiza o contador do passo 1/7", async () => {
    render(<SetupWizard userId="u1" onComplete={vi.fn()} />);
    await waitFor(() => expect(screen.getByText("1 / 7")).toBeInTheDocument());
  });
});

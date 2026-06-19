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
  it("returns false when flag is not set", () => {
    expect(isOnboardingDone("u1")).toBe(false);
  });

  it("returns true when user flag is marked", () => {
    localStorage.setItem("vectora:onboarding-done-u1", "1");
    expect(isOnboardingDone("u1")).toBe(true);
  });

  it("isolates flag per user — another user flag does not apply", () => {
    localStorage.setItem("vectora:onboarding-done-u1", "1");
    expect(isOnboardingDone("u2")).toBe(false);
  });

  it("flag from unrelated userId does not grant access", () => {
    localStorage.setItem("vectora:onboarding-done-admin", "1");
    expect(isOnboardingDone("u1")).toBe(false);
    expect(isOnboardingDone("u2")).toBe(false);
  });
});

describe("SetupWizard", () => {
  it("renders step counter 1/7 on first step", async () => {
    render(<SetupWizard userId="u1" onComplete={vi.fn()} />);
    await waitFor(() => expect(screen.getByText("1 / 7")).toBeInTheDocument());
  });

  it("content area has fixed min-height data-testid", async () => {
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
    next(); // step 0 → 1
    await waitFor(() => screen.getByText("2 / 7"));
    next(); // step 1 → 2
    await waitFor(() => screen.getByText("3 / 7"));
  }

  it("token input has autocomplete=off to disable browser autofill", async () => {
    await renderAtStepToken();
    const input = screen.getByPlaceholderText("vct_…");
    expect(input).toHaveAttribute("autocomplete", "off");
  });

  it("token input does not have any semantic autocomplete hint", async () => {
    await renderAtStepToken();
    const input = screen.getByPlaceholderText("vct_…");
    expect(input).not.toHaveAttribute("autocomplete", "new-password");
    expect(input).not.toHaveAttribute("autocomplete", "current-password");
    expect(input).not.toHaveAttribute("autocomplete", "email");
  });

  it("'Sign in with account' button opens vectora.company in external browser", async () => {
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

  it("'Sign in with account' must not open a localhost/internal URL", async () => {
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

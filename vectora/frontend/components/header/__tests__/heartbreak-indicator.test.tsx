// @vitest-environment jsdom
/**
 * HeartbreakIndicator — testes de renderização (Sprint 9).
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, cleanup, act } from "@testing-library/react";

// ── fetch mock ───────────────────────────────────────────────────────────────

let SESSIONS: object[] = [];

const FETCH_MOCK = vi.fn(async (url: string, opts?: RequestInit) => {
  const method = opts?.method ?? "GET";
  if (method === "DELETE") {
    return new Response(null, { status: 204 });
  }
  return new Response(JSON.stringify(SESSIONS), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
});

beforeEach(() => {
  vi.stubGlobal("fetch", FETCH_MOCK);
  SESSIONS = [];
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

// ── mocks ────────────────────────────────────────────────────────────────────

vi.mock("@/lib/paraglide/messages", () => ({
  m: new Proxy(
    {},
    {
      get:
        (_t, prop) =>
        (..._args: unknown[]) =>
          String(prop),
    },
  ),
}));

// ── testes ───────────────────────────────────────────────────────────────────

async function renderIndicator() {
  const { HeartbreakIndicator } = await import("../heartbreak-indicator");
  return render(<HeartbreakIndicator />);
}

describe("HeartbreakIndicator (Sprint 9)", () => {
  it("não renderiza nada quando não há sessões ativas", async () => {
    SESSIONS = [];
    await act(async () => {
      await renderIndicator();
    });
    expect(
      document.querySelector("[data-testid='heartbreak-indicator']"),
    ).toBeNull();
  });

  it("exibe bolinha pulsante quando há sessão ativa", async () => {
    SESSIONS = [
      {
        id: "s1",
        instruction: "monitore X",
        status: "active",
        run_count: 3,
        trigger_count: 1,
      },
    ];
    await act(async () => {
      await renderIndicator();
    });
    expect(
      document.querySelector("[data-testid='heartbreak-dot']"),
    ).not.toBeNull();
  });

  it("indicador tem aria-label correto", async () => {
    SESSIONS = [
      {
        id: "s1",
        instruction: "monitore X",
        status: "active",
        run_count: 0,
        trigger_count: 1,
      },
    ];
    await act(async () => {
      await renderIndicator();
    });
    const btn = document.querySelector(
      "[data-testid='heartbreak-indicator']",
    ) as HTMLElement;
    expect(btn?.getAttribute("aria-label")).toBeTruthy();
  });
});

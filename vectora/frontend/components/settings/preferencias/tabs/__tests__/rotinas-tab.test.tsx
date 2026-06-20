// @vitest-environment jsdom
/**
 * RotinasTab — testes de renderização e interações (Sprint 8).
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  render,
  screen,
  cleanup,
  fireEvent,
  act,
} from "@testing-library/react";

// ── fetch mock ───────────────────────────────────────────────────────────────

const ROUTINES: object[] = [];

const FETCH_MOCK = vi.fn(async (url: string, opts?: RequestInit) => {
  const method = opts?.method ?? "GET";
  if (method === "GET" && String(url).includes("/routines")) {
    return new Response(JSON.stringify(ROUTINES), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  }
  if (method === "POST") {
    const body = JSON.parse(String(opts?.body ?? "{}"));
    return new Response(
      JSON.stringify({
        id: "new-1",
        name: body.name,
        instruction: body.instruction,
        cron_expr: body.cron_expr,
        enabled: true,
        last_run_at: null,
        next_run_at: "2024-06-21T09:00:00",
      }),
      { status: 201, headers: { "Content-Type": "application/json" } },
    );
  }
  if (method === "DELETE") {
    return new Response(null, { status: 204 });
  }
  return new Response(JSON.stringify({}), { status: 200 });
});

beforeEach(() => {
  vi.stubGlobal("fetch", FETCH_MOCK);
  ROUTINES.length = 0;
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

// ── mocks ────────────────────────────────────────────────────────────────────

vi.mock("@/lib/stores/toast-store", () => ({
  useToastStore: { getState: () => ({ success: vi.fn(), error: vi.fn() }) },
}));

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

async function renderTab() {
  const { RotinasTab } = await import("../rotinas-tab");
  return render(<RotinasTab />);
}

describe("RotinasTab (Sprint 8)", () => {
  it("exibe mensagem de lista vazia quando não há rotinas", async () => {
    await act(async () => {
      await renderTab();
    });
    expect(document.querySelector("[data-testid='routine-item']")).toBeNull();
  });

  it("botão 'Nova rotina' abre o dialog de criação", async () => {
    await act(async () => {
      await renderTab();
    });
    const btn = document.querySelector(
      "[data-testid='routines-new-btn']",
    ) as HTMLElement;
    expect(btn).not.toBeNull();
    await act(async () => {
      fireEvent.click(btn);
    });
    expect(
      document.querySelector("[data-testid='routine-name-input']"),
    ).not.toBeNull();
  });

  it("salvar rotina chama POST /routines e exibe novo item", async () => {
    await act(async () => {
      await renderTab();
    });
    const newBtn = document.querySelector(
      "[data-testid='routines-new-btn']",
    ) as HTMLElement;
    await act(async () => {
      fireEvent.click(newBtn);
    });
    const nameInput = document.querySelector(
      "[data-testid='routine-name-input']",
    ) as HTMLInputElement;
    const instrInput = document.querySelector(
      "[data-testid='routine-instruction-input']",
    ) as HTMLTextAreaElement;
    await act(async () => {
      fireEvent.change(nameInput, { target: { value: "Minha rotina" } });
      fireEvent.change(instrInput, { target: { value: "faça X" } });
    });
    const saveBtn = document.querySelector(
      "[data-testid='routine-save-btn']",
    ) as HTMLElement;
    await act(async () => {
      fireEvent.click(saveBtn);
    });
    expect(
      document.querySelector("[data-testid='routine-item']"),
    ).not.toBeNull();
  });
});

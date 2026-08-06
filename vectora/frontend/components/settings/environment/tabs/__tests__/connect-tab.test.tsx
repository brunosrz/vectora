// @vitest-environment jsdom
/**
 * Testes da ConnectTab.
 *
 * Cobre:
 * - Badge Pro visível nos 3 blocos (Telegram, Discord, Email)
 * - Salvar configurações preenchidas: POST /auth/envs com o payload certo
 * - Erro/borda: resposta não-ok do backend (ex.: 402 sem Pro) mostra toast
 *   de erro em vez de sucesso silencioso
 */

import { describe, it, expect, vi, afterEach, beforeEach } from "vitest";
import {
  render,
  screen,
  cleanup,
  fireEvent,
  waitFor,
} from "@testing-library/react";

const { useLicenseStatusMock } = vi.hoisted(() => ({
  useLicenseStatusMock: vi.fn(),
}));
const { toastErrorMock, toastSuccessMock, toastWarningMock } = vi.hoisted(
  () => ({
    toastErrorMock: vi.fn(),
    toastSuccessMock: vi.fn(),
    toastWarningMock: vi.fn(),
  }),
);

vi.mock("@/lib/hooks/use-license-status", () => ({
  useLicenseStatus: useLicenseStatusMock,
}));

vi.mock("@/lib/stores/toast-store", () => ({
  useToastStore: {
    getState: () => ({
      error: toastErrorMock,
      success: toastSuccessMock,
      warning: toastWarningMock,
    }),
  },
}));

const { ConnectTab } = await import("../connect-tab");

beforeEach(() => {
  useLicenseStatusMock.mockReturnValue({
    status: { configured: false, tier: null, status: "unknown" },
    loading: false,
    refetch: vi.fn(),
  });
  toastErrorMock.mockClear();
  toastSuccessMock.mockClear();
  toastWarningMock.mockClear();
});

afterEach(cleanup);

describe("ConnectTab", () => {
  it("mostra o badge Pro nos 3 blocos de plataforma", () => {
    render(<ConnectTab />);
    expect(screen.getAllByText("Pro")).toHaveLength(3);
  });

  it("salva as configurações preenchidas via POST /auth/envs", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue({ ok: true, json: async () => ({}) });
    vi.stubGlobal("fetch", fetchMock);

    render(<ConnectTab />);
    fireEvent.change(screen.getByPlaceholderText(/123456789:ABC/), {
      target: { value: "123:abc" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Salvar/ }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toBe("/auth/envs");
    expect(JSON.parse(options.body)).toEqual([
      { key: "TELEGRAM_BOT_TOKEN", value: "123:abc" },
    ]);
    await waitFor(() => expect(toastSuccessMock).toHaveBeenCalled());

    vi.unstubAllGlobals();
  });

  it("erro/borda: resposta não-ok (ex.: 402 sem Pro) mostra toast de erro", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: false, status: 402 });
    vi.stubGlobal("fetch", fetchMock);

    render(<ConnectTab />);
    fireEvent.change(screen.getByPlaceholderText(/123456789:ABC/), {
      target: { value: "123:abc" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Salvar/ }));

    await waitFor(() => expect(toastErrorMock).toHaveBeenCalled());
    expect(toastSuccessMock).not.toHaveBeenCalled();

    vi.unstubAllGlobals();
  });
});

import { describe, it, expect, vi, beforeEach } from "vitest";

import { exportData, requestAccountDeletion } from "./gdpr";

const { mockServicesFetch, mockClearSessionCookie } = vi.hoisted(() => ({
  mockServicesFetch: vi.fn(),
  mockClearSessionCookie: vi.fn(),
}));

vi.mock("#/lib/services/client", () => ({
  servicesFetch: mockServicesFetch,
  clearSessionCookie: mockClearSessionCookie,
}));

beforeEach(() => {
  vi.clearAllMocks();
});

describe("exportData", () => {
  it("retorna a URL pré-assinada do export", async () => {
    mockServicesFetch.mockResolvedValue({ url: "https://r2.test/export.json" });

    const result = await exportData();

    expect(result).toEqual({ url: "https://r2.test/export.json" });
    expect(mockClearSessionCookie).not.toHaveBeenCalled();
  });
});

describe("requestAccountDeletion", () => {
  it("limpa a sessão após a exclusão ser aceita pelo worker", async () => {
    mockServicesFetch.mockResolvedValue({ ok: true });

    const result = await requestAccountDeletion();

    expect(result).toEqual({ ok: true });
    expect(mockClearSessionCookie).toHaveBeenCalledTimes(1);
  });

  it("não limpa a sessão quando o worker recusa a exclusão (edge)", async () => {
    mockServicesFetch.mockRejectedValue(new Error("services_error_403"));

    await expect(requestAccountDeletion()).rejects.toThrowError(
      "services_error_403",
    );
    expect(mockClearSessionCookie).not.toHaveBeenCalled();
  });
});

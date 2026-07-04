import { describe, it, expect, vi, beforeEach } from "vitest";

import { authorizeDevice } from "./oauth";

const { mockServicesFetch } = vi.hoisted(() => ({
  mockServicesFetch: vi.fn(),
}));

vi.mock("#/lib/services/client", () => ({
  servicesFetch: mockServicesFetch,
}));

beforeEach(() => {
  vi.clearAllMocks();
});

describe("authorizeDevice", () => {
  it("autoriza o device com o state informado", async () => {
    mockServicesFetch.mockResolvedValue({ ok: true });

    const result = await authorizeDevice({ data: { state: "device-state-1" } });

    expect(result).toEqual({ ok: true });
    expect(mockServicesFetch).toHaveBeenCalledWith(
      "/oauth/device",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("rejeita state vazio (edge — validação Zod min(1))", async () => {
    await expect(authorizeDevice({ data: { state: "" } })).rejects.toBeTruthy();
    expect(mockServicesFetch).not.toHaveBeenCalled();
  });
});

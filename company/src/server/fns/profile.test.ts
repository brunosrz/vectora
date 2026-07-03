import { describe, it, expect, vi, beforeEach } from "vitest";

import { updateProfile } from "./profile";

const { mockServicesFetch } = vi.hoisted(() => ({
  mockServicesFetch: vi.fn(),
}));

vi.mock("#/lib/services/client", () => ({
  servicesFetch: mockServicesFetch,
}));

beforeEach(() => {
  vi.clearAllMocks();
});

describe("updateProfile", () => {
  it("atualiza todos os campos quando informados", async () => {
    mockServicesFetch.mockResolvedValue({ ok: true });

    const result = await updateProfile({
      data: { full_name: "Nome Novo", country: "BR", language: "pt" },
    });

    expect(result).toEqual({ ok: true });
  });

  it("funciona sem nenhum campo (edge — todos opcionais)", async () => {
    mockServicesFetch.mockResolvedValue({ ok: true });

    await expect(updateProfile({ data: {} })).resolves.toEqual({ ok: true });
  });

  it("rejeita full_name com 1 caractere (edge — validação Zod min(2))", async () => {
    await expect(
      updateProfile({ data: { full_name: "A" } }),
    ).rejects.toBeTruthy();
  });

  it("rejeita country fora do enum BR/INTL (edge)", async () => {
    await expect(
      updateProfile({ data: { country: "US" as never } }),
    ).rejects.toBeTruthy();
  });
});

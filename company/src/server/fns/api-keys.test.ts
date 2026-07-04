import { describe, it, expect, vi, beforeEach } from "vitest";

import { listApiKeys, createApiKey, revokeApiKey } from "./api-keys";

const { mockServicesFetch } = vi.hoisted(() => ({
  mockServicesFetch: vi.fn(),
}));

vi.mock("#/lib/services/client", () => ({
  servicesFetch: mockServicesFetch,
}));

beforeEach(() => {
  vi.clearAllMocks();
});

describe("listApiKeys", () => {
  it("retorna a lista de chaves", async () => {
    mockServicesFetch.mockResolvedValue([
      { id: "k1", name: "CI", scopes: ["read"] },
    ]);
    await expect(listApiKeys()).resolves.toHaveLength(1);
  });

  it("retorna array vazio quando o usuário não tem chaves (edge)", async () => {
    mockServicesFetch.mockResolvedValue([]);
    await expect(listApiKeys()).resolves.toEqual([]);
  });
});

describe("createApiKey", () => {
  it("cria a chave com nome e scopes válidos", async () => {
    mockServicesFetch.mockResolvedValue({ secret: "sk_abc123" });

    const result = await createApiKey({
      data: { name: "Deploy CI", scopes: ["read", "write"] },
    });

    expect(result).toEqual({ secret: "sk_abc123" });
  });

  it("rejeita nome vazio (edge — validação Zod min(1))", async () => {
    await expect(
      createApiKey({ data: { name: "", scopes: ["read"] } }),
    ).rejects.toBeTruthy();
    expect(mockServicesFetch).not.toHaveBeenCalled();
  });

  it("rejeita nome acima de 64 caracteres (edge — validação Zod max(64))", async () => {
    await expect(
      createApiKey({ data: { name: "x".repeat(65), scopes: ["read"] } }),
    ).rejects.toBeTruthy();
  });

  it("rejeita scope fora do enum permitido (edge)", async () => {
    await expect(
      createApiKey({
        data: { name: "Deploy", scopes: ["superadmin" as never] },
      }),
    ).rejects.toBeTruthy();
  });

  it("aceita array de scopes vazio (edge — schema não exige mínimo)", async () => {
    mockServicesFetch.mockResolvedValue({ secret: "sk_noscopes" });
    await expect(
      createApiKey({ data: { name: "Sem escopo", scopes: [] } }),
    ).resolves.toEqual({ secret: "sk_noscopes" });
  });
});

describe("revokeApiKey", () => {
  it("revoga a chave pelo id (UUID válido)", async () => {
    mockServicesFetch.mockResolvedValue({ ok: true });

    const result = await revokeApiKey({
      data: { id: "550e8400-e29b-41d4-a716-446655440000" },
    });

    expect(result).toEqual({ ok: true });
    expect(mockServicesFetch).toHaveBeenCalledWith(
      "/api-keys/550e8400-e29b-41d4-a716-446655440000/revoke",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("rejeita id que não é UUID (edge — validação Zod)", async () => {
    await expect(
      revokeApiKey({ data: { id: "not-a-uuid" } }),
    ).rejects.toBeTruthy();
    expect(mockServicesFetch).not.toHaveBeenCalled();
  });
});

import { describe, it, expect, vi, beforeEach } from "vitest";

import { submitIssue, listOpenIssues, joinWaitlist } from "./issues";

const { mockServicesFetch } = vi.hoisted(() => ({
  mockServicesFetch: vi.fn(),
}));

vi.mock("#/lib/services/client", () => ({
  servicesFetch: mockServicesFetch,
}));

beforeEach(() => {
  vi.clearAllMocks();
});

describe("submitIssue", () => {
  const base = {
    title: "Bug ao revelar token",
    category: "bug" as const,
    turnstileToken: "tt-1",
  };

  it("envia o issue com descrição e email opcionais preenchidos", async () => {
    mockServicesFetch.mockResolvedValue({ ok: true });

    const result = await submitIssue({
      data: { ...base, description: "Não funciona", email: "a@b.com" },
    });

    expect(result).toEqual({ ok: true });
  });

  it("aceita email como string vazia (edge — schema permite email opcional ou '')", async () => {
    mockServicesFetch.mockResolvedValue({ ok: true });

    await expect(
      submitIssue({ data: { ...base, email: "" } }),
    ).resolves.toEqual({ ok: true });
  });

  it("rejeita título com menos de 3 caracteres (edge — validação Zod)", async () => {
    await expect(
      submitIssue({ data: { ...base, title: "ab" } }),
    ).rejects.toBeTruthy();
  });

  it("rejeita categoria fora do enum (edge)", async () => {
    await expect(
      submitIssue({ data: { ...base, category: "spam" as never } }),
    ).rejects.toBeTruthy();
  });

  it("rejeita descrição acima de 5000 caracteres (edge)", async () => {
    await expect(
      submitIssue({ data: { ...base, description: "x".repeat(5001) } }),
    ).rejects.toBeTruthy();
  });
});

describe("listOpenIssues", () => {
  it("retorna a lista de issues abertas", async () => {
    mockServicesFetch.mockResolvedValue([
      {
        id: "1",
        title: "Bug X",
        category: "bug",
        description: null,
        created_at: "now",
      },
    ]);

    await expect(listOpenIssues()).resolves.toHaveLength(1);
  });

  it("retorna array vazio quando não há issues (edge)", async () => {
    mockServicesFetch.mockResolvedValue([]);
    await expect(listOpenIssues()).resolves.toEqual([]);
  });
});

describe("joinWaitlist", () => {
  it("entra na waitlist com source informado", async () => {
    mockServicesFetch.mockResolvedValue({ ok: true });

    const result = await joinWaitlist({
      data: { email: "a@b.com", turnstileToken: "tt-1", source: "landing" },
    });

    expect(result).toEqual({ ok: true });
  });

  it("funciona sem 'source' (edge — campo opcional)", async () => {
    mockServicesFetch.mockResolvedValue({ ok: true });

    await expect(
      joinWaitlist({ data: { email: "a@b.com", turnstileToken: "tt-1" } }),
    ).resolves.toEqual({ ok: true });
  });

  it("rejeita email inválido (edge — validação Zod)", async () => {
    await expect(
      joinWaitlist({
        data: { email: "invalido", turnstileToken: "tt-1" },
      }),
    ).rejects.toBeTruthy();
    expect(mockServicesFetch).not.toHaveBeenCalled();
  });
});

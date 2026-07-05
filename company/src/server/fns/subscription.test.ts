import { describe, it, expect, vi, beforeEach } from "vitest";

import {
  getSubscription,
  createCheckout,
  createPortal,
  getLicenseHistory,
} from "./subscription";

const { mockServicesFetch } = vi.hoisted(() => ({
  mockServicesFetch: vi.fn(),
}));

vi.mock("#/lib/services/client", () => ({
  servicesFetch: mockServicesFetch,
}));

beforeEach(() => {
  vi.clearAllMocks();
});

describe("getSubscription", () => {
  it("retorna a assinatura quando existe", async () => {
    mockServicesFetch.mockResolvedValue({
      id: "sub1",
      tier: "pro",
      status: "active",
      currency: "BRL",
    });

    const result = await getSubscription();

    expect(result).toMatchObject({ tier: "pro", status: "active" });
  });

  it("retorna null quando o worker responde 'not_found' (edge — usuário free sem assinatura)", async () => {
    mockServicesFetch.mockRejectedValue(new Error("not_found"));

    await expect(getSubscription()).resolves.toBeNull();
  });

  it("propaga qualquer outro erro (edge — não confunde erro real com not_found)", async () => {
    mockServicesFetch.mockRejectedValue(new Error("services_error_500"));

    await expect(getSubscription()).rejects.toThrowError("services_error_500");
  });

  it("propaga erros que não são instância de Error (edge)", async () => {
    mockServicesFetch.mockRejectedValue("string de erro crua");

    await expect(getSubscription()).rejects.toBe("string de erro crua");
  });
});

describe("createCheckout", () => {
  it("retorna a URL de checkout e envia plan_id/coupon_code pro worker", async () => {
    mockServicesFetch.mockResolvedValue({ url: "https://checkout.test/abc" });

    const result = await createCheckout({
      data: { planId: "3m", couponCode: "GALEGO" },
    });

    expect(result).toEqual({ url: "https://checkout.test/abc" });
    expect(mockServicesFetch).toHaveBeenCalledWith(
      "/billing/checkout",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ plan_id: "3m", coupon_code: "GALEGO" }),
      }),
    );
  });

  it("aceita um checkout sem cupom e retorna { redeemed: true } para cupom free_lifetime (edge)", async () => {
    mockServicesFetch.mockResolvedValue({ redeemed: true });

    const result = await createCheckout({ data: { planId: "1m" } });

    expect(result).toEqual({ redeemed: true });
  });

  it("rejeita um plan_id vazio antes de bater na rede (edge — validação Zod)", async () => {
    await expect(createCheckout({ data: { planId: "" } })).rejects.toBeTruthy();
    expect(mockServicesFetch).not.toHaveBeenCalled();
  });
});

describe("createPortal", () => {
  it("retorna a URL do portal de billing", async () => {
    mockServicesFetch.mockResolvedValue({ url: "https://portal.test/abc" });

    const result = await createPortal();

    expect(result).toEqual({ url: "https://portal.test/abc" });
  });
});

describe("getLicenseHistory", () => {
  it("retorna a lista de validações", async () => {
    mockServicesFetch.mockResolvedValue([
      { id: "1", result: "valid" },
      { id: "2", result: "expired" },
    ]);

    const result = await getLicenseHistory();

    expect(result).toHaveLength(2);
  });

  it("retorna array vazio quando não há histórico (edge)", async () => {
    mockServicesFetch.mockResolvedValue([]);

    await expect(getLicenseHistory()).resolves.toEqual([]);
  });
});

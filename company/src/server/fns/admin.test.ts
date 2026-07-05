import { describe, it, expect, vi, beforeEach } from "vitest";

import {
  listUsers,
  listCoupons,
  createCoupon,
  deactivateCoupon,
  listGifts,
  createGift,
} from "./admin";

const { mockServicesFetch } = vi.hoisted(() => ({
  mockServicesFetch: vi.fn(),
}));

vi.mock("#/lib/services/client", () => ({
  servicesFetch: mockServicesFetch,
}));

beforeEach(() => {
  vi.clearAllMocks();
});

describe("listUsers", () => {
  it("chama /admin/users sem query string quando limit/offset não são passados", async () => {
    mockServicesFetch.mockResolvedValue({ users: [] });
    await listUsers({ data: {} });
    expect(mockServicesFetch).toHaveBeenCalledWith("/admin/users");
  });

  it("monta a query string com limit/offset quando fornecidos", async () => {
    mockServicesFetch.mockResolvedValue({ users: [] });
    await listUsers({ data: { limit: 50, offset: 100 } });
    expect(mockServicesFetch).toHaveBeenCalledWith(
      "/admin/users?limit=50&offset=100",
    );
  });
});

describe("listCoupons", () => {
  it("retorna a lista de cupons", async () => {
    mockServicesFetch.mockResolvedValue({ coupons: [{ id: "c1" }] });
    await expect(listCoupons()).resolves.toEqual({ coupons: [{ id: "c1" }] });
  });
});

describe("createCoupon", () => {
  it("cria um cupom de desconto com planos", async () => {
    mockServicesFetch.mockResolvedValue({ ok: true, code: "GALEGO" });

    const result = await createCoupon({
      data: {
        code: "galego",
        kind: "discount",
        grant_plan_id: "3m",
        charge_plan_id: "1m",
      },
    });

    expect(result).toEqual({ ok: true, code: "GALEGO" });
    expect(mockServicesFetch).toHaveBeenCalledWith(
      "/admin/coupons",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("rejeita um código com menos de 3 caracteres (edge — validação Zod)", async () => {
    await expect(
      createCoupon({ data: { code: "ab", kind: "discount" } }),
    ).rejects.toBeTruthy();
    expect(mockServicesFetch).not.toHaveBeenCalled();
  });

  it("aceita um cupom free_lifetime sem os campos de plano", async () => {
    mockServicesFetch.mockResolvedValue({ ok: true, code: "SECRET1" });
    await expect(
      createCoupon({ data: { code: "SECRET1", kind: "free_lifetime" } }),
    ).resolves.toEqual({ ok: true, code: "SECRET1" });
  });
});

describe("deactivateCoupon", () => {
  it("desativa o cupom pelo id", async () => {
    mockServicesFetch.mockResolvedValue({ ok: true });
    await deactivateCoupon({ data: { id: "coupon-1" } });
    expect(mockServicesFetch).toHaveBeenCalledWith(
      "/admin/coupons/coupon-1/deactivate",
      expect.objectContaining({ method: "POST" }),
    );
  });
});

describe("listGifts", () => {
  it("retorna a lista de presentes", async () => {
    mockServicesFetch.mockResolvedValue({ gifts: [] });
    await expect(listGifts()).resolves.toEqual({ gifts: [] });
  });
});

describe("createGift", () => {
  it("cria um presente com duração", async () => {
    mockServicesFetch.mockResolvedValue({
      ok: true,
      gift_id: "g1",
      claimed: false,
    });

    const result = await createGift({
      data: { email: "friend@example.com", duration_months: 6 },
    });

    expect(result).toEqual({ ok: true, gift_id: "g1", claimed: false });
  });

  it("rejeita um email inválido (edge — validação Zod)", async () => {
    await expect(
      createGift({ data: { email: "not-an-email" } }),
    ).rejects.toBeTruthy();
    expect(mockServicesFetch).not.toHaveBeenCalled();
  });

  it("aceita presente vitalício sem duration_months (edge)", async () => {
    mockServicesFetch.mockResolvedValue({
      ok: true,
      gift_id: "g2",
      claimed: true,
    });
    await expect(
      createGift({ data: { email: "lifetime@example.com" } }),
    ).resolves.toMatchObject({ claimed: true });
  });
});

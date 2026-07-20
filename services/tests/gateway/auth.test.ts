import { describe, it, expect } from "vitest";
import { timingSafeEqual, generateGatewayToken } from "../../src/gateway/auth";

const HMAC_SECRET = "test-hmac-secret-32-chars-minimum";

describe("timingSafeEqual", () => {
  it("retorna true para strings idênticas", () => {
    expect(timingSafeEqual("Bearer secret-123", "Bearer secret-123")).toBe(
      true,
    );
  });

  it("retorna false para strings diferentes de mesmo tamanho", () => {
    expect(timingSafeEqual("Bearer secret-123", "Bearer secret-456")).toBe(
      false,
    );
  });

  it("retorna false para strings de tamanhos diferentes (edge)", () => {
    expect(timingSafeEqual("Bearer short", "Bearer much-longer-secret")).toBe(
      false,
    );
  });

  it("retorna false comparando com string vazia", () => {
    expect(timingSafeEqual("Bearer secret", "")).toBe(false);
  });
});

describe("generateGatewayToken", () => {
  it("retorna string de 6 chars alfanuméricos", async () => {
    const token = await generateGatewayToken("fp-abc", HMAC_SECRET);
    expect(token).toMatch(/^[a-z0-9]{6}$/);
  });

  it("é determinístico — mesmo fingerprint gera mesmo token", async () => {
    const a = await generateGatewayToken("fp-abc", HMAC_SECRET);
    const b = await generateGatewayToken("fp-abc", HMAC_SECRET);
    expect(a).toBe(b);
  });

  it("é diferente para fingerprints distintos", async () => {
    const a = await generateGatewayToken("fp-laptop", HMAC_SECRET);
    const b = await generateGatewayToken("fp-desktop", HMAC_SECRET);
    expect(a).not.toBe(b);
  });

  it("é diferente com secrets distintos pro mesmo fingerprint (edge)", async () => {
    const a = await generateGatewayToken("fp-abc", HMAC_SECRET);
    const b = await generateGatewayToken(
      "fp-abc",
      "outro-secret-32-chars-min!",
    );
    expect(a).not.toBe(b);
  });
});

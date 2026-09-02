import { describe, it, expect } from "vitest";
import {
  timingSafeEqual,
  generateGatewayToken,
  generateConnectorSecret,
  hashConnectorSecret,
} from "../../src/gateway/auth";

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
  it("retorna string de 10 chars alfanuméricos", async () => {
    const token = await generateGatewayToken("fp-abc", HMAC_SECRET);
    expect(token).toMatch(/^[a-z0-9]{10}$/);
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

  it("erro de borda — sem colisão observável num lote grande de fingerprints distintos", async () => {
    // Regressão do bug real: o esquema antigo (6 chars, só 4 bytes do HMAC,
    // `.slice(-6)` sobre um valor de até 32 bits) descartava dígito(s) mais
    // significativo(s) sempre que o valor excedia 36^6 — colidindo
    // fingerprints diferentes no mesmo token em >46% dos casos. Não dá pra
    // provar "zero colisão" com um teste, mas um lote de 2000 fingerprints
    // distintos gerando 2000 tokens distintos já falsearia o bug antigo
    // (que colidia com frequência alta o bastante pra aparecer facilmente
    // numa amostra desse tamanho).
    const tokens = new Set<string>();
    for (let i = 0; i < 2000; i++) {
      tokens.add(await generateGatewayToken(`fp-${i}`, HMAC_SECRET));
    }
    expect(tokens.size).toBe(2000);
  });
});

describe("generateConnectorSecret", () => {
  it("gera 32 bytes de entropia como base64url sem padding (43 chars)", () => {
    const secret = generateConnectorSecret();
    expect(secret).toMatch(/^[A-Za-z0-9_-]{43}$/);
  });

  it("é diferente a cada chamada (aleatório, não determinístico)", () => {
    const a = generateConnectorSecret();
    const b = generateConnectorSecret();
    expect(a).not.toBe(b);
  });
});

describe("hashConnectorSecret", () => {
  it("é determinístico — mesmo secret gera mesmo hash", async () => {
    const secret = generateConnectorSecret();
    const a = await hashConnectorSecret(secret);
    const b = await hashConnectorSecret(secret);
    expect(a).toBe(b);
  });

  it("hash é diferente do secret original (não é passthrough)", async () => {
    const secret = generateConnectorSecret();
    const hash = await hashConnectorSecret(secret);
    expect(hash).not.toBe(secret);
    expect(hash).toMatch(/^[0-9a-f]{64}$/);
  });

  it("secrets diferentes geram hashes diferentes (edge)", async () => {
    const a = await hashConnectorSecret(generateConnectorSecret());
    const b = await hashConnectorSecret(generateConnectorSecret());
    expect(a).not.toBe(b);
  });
});

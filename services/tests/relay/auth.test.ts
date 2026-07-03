import { describe, it, expect } from "vitest";
import { verifyJwt, generateRelayToken } from "../../src/relay/auth";

const JWT_SECRET = "test-jwt-secret-32-chars-minimum!";
const HMAC_SECRET = "test-hmac-secret-32-chars-minimum";

async function signJwt(payload: object, secret: string): Promise<string> {
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const header = btoa(JSON.stringify({ alg: "HS256", typ: "JWT" }))
    .replace(/=/g, "")
    .replace(/\+/g, "-")
    .replace(/\//g, "_");
  const body = btoa(JSON.stringify(payload))
    .replace(/=/g, "")
    .replace(/\+/g, "-")
    .replace(/\//g, "_");
  const data = `${header}.${body}`;
  const sig = await crypto.subtle.sign(
    "HMAC",
    key,
    new TextEncoder().encode(data),
  );
  const sigB64 = btoa(String.fromCharCode(...new Uint8Array(sig)))
    .replace(/=/g, "")
    .replace(/\+/g, "-")
    .replace(/\//g, "_");
  return `${data}.${sigB64}`;
}

describe("verifyJwt", () => {
  it("retorna payload para JWT válido", async () => {
    const now = Math.floor(Date.now() / 1000);
    const token = await signJwt(
      { sub: "user-123", exp: now + 3600, iat: now },
      JWT_SECRET,
    );
    const payload = await verifyJwt(token, JWT_SECRET);
    expect(payload.sub).toBe("user-123");
  });

  it("lança erro para JWT expirado", async () => {
    const now = Math.floor(Date.now() / 1000);
    const token = await signJwt(
      { sub: "user-123", exp: now - 1, iat: now - 100 },
      JWT_SECRET,
    );
    await expect(verifyJwt(token, JWT_SECRET)).rejects.toThrow("expired");
  });

  it("lança erro para assinatura inválida", async () => {
    const now = Math.floor(Date.now() / 1000);
    const token = await signJwt(
      { sub: "user-123", exp: now + 3600, iat: now },
      "wrong-secret-for-signing-jwt!!",
    );
    await expect(verifyJwt(token, JWT_SECRET)).rejects.toThrow("invalid");
  });

  it("lança erro para JWT malformado", async () => {
    await expect(verifyJwt("not.a.jwt", JWT_SECRET)).rejects.toThrow();
  });

  it("lança erro para JWT sem sub", async () => {
    const now = Math.floor(Date.now() / 1000);
    const token = await signJwt({ exp: now + 3600, iat: now }, JWT_SECRET);
    await expect(verifyJwt(token, JWT_SECRET)).rejects.toThrow("sub");
  });
});

describe("generateRelayToken", () => {
  it("retorna string de 6 chars alfanuméricos", async () => {
    const token = await generateRelayToken("user-123", "fp-abc", HMAC_SECRET);
    expect(token).toMatch(/^[a-z0-9]{6}$/);
  });

  it("é determinístico — mesmo input gera mesmo token", async () => {
    const a = await generateRelayToken("user-123", "fp-abc", HMAC_SECRET);
    const b = await generateRelayToken("user-123", "fp-abc", HMAC_SECRET);
    expect(a).toBe(b);
  });

  it("é diferente para users distintos", async () => {
    const a = await generateRelayToken("user-111", "fp-abc", HMAC_SECRET);
    const b = await generateRelayToken("user-222", "fp-abc", HMAC_SECRET);
    expect(a).not.toBe(b);
  });

  it("é diferente para fingerprints distintos", async () => {
    const a = await generateRelayToken("user-123", "fp-laptop", HMAC_SECRET);
    const b = await generateRelayToken("user-123", "fp-desktop", HMAC_SECRET);
    expect(a).not.toBe(b);
  });
});

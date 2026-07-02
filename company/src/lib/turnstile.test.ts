import { describe, it, expect, vi, afterEach } from "vitest";
import { verifyTurnstile } from "./turnstile";

// Contrato do verifyTurnstile: em dev (ou sem TURNSTILE_SECRET_KEY) dispensa a
// verificação (o widget da Cloudflare não conecta no localhost); em produção
// valida o token contra o siteverify da Cloudflare.

const originalSecret = process.env.TURNSTILE_SECRET_KEY;

afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
  if (originalSecret === undefined) delete process.env.TURNSTILE_SECRET_KEY;
  else process.env.TURNSTILE_SECRET_KEY = originalSecret;
});

describe("verifyTurnstile", () => {
  it("dispensa em dev sem chamar o siteverify", async () => {
    vi.stubEnv("DEV", true);
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    const res = await verifyTurnstile("qualquer-token");

    expect(res.success).toBe(true);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("dispensa quando não há TURNSTILE_SECRET_KEY (mesmo fora de dev)", async () => {
    vi.stubEnv("DEV", false);
    delete process.env.TURNSTILE_SECRET_KEY;
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    const res = await verifyTurnstile("qualquer-token");

    expect(res.success).toBe(true);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("em produção valida o token contra o siteverify (sucesso)", async () => {
    vi.stubEnv("DEV", false);
    process.env.TURNSTILE_SECRET_KEY = "sekret";
    const fetchMock = vi.fn(async () => ({
      json: async () => ({ success: true }),
    }));
    vi.stubGlobal("fetch", fetchMock);

    const res = await verifyTurnstile("token-valido", "1.2.3.4");

    expect(res.success).toBe(true);
    expect(fetchMock).toHaveBeenCalledOnce();
    // o remoteip é repassado quando fornecido
    const body = JSON.parse(
      (fetchMock.mock.calls[0][1] as RequestInit).body as string,
    );
    expect(body).toMatchObject({
      secret: "sekret",
      response: "token-valido",
      remoteip: "1.2.3.4",
    });
  });

  it("token inválido → success false com os error codes (par de erro)", async () => {
    vi.stubEnv("DEV", false);
    process.env.TURNSTILE_SECRET_KEY = "sekret";
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        json: async () => ({
          success: false,
          "error-codes": ["invalid-input-response"],
        }),
      })),
    );

    const res = await verifyTurnstile("token-ruim");

    expect(res.success).toBe(false);
    expect(res.errorCodes).toEqual(["invalid-input-response"]);
  });
});

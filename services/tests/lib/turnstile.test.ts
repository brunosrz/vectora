import { describe, expect, it, vi, afterEach } from "vitest";
import { verifyTurnstile } from "../../src/lib/turnstile";

describe("verifyTurnstile", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("bypassa quando secretKey não está definido (dev)", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    const res = await verifyTurnstile("any-token", undefined);

    expect(res).toEqual({ success: true });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("valida contra o siteverify quando secretKey está presente, repassando o ip", async () => {
    const fetchMock = vi.fn(async (_url: string, init: RequestInit) => {
      const body = JSON.parse(init.body as string);
      expect(body).toEqual({
        secret: "sekret",
        response: "tok",
        remoteip: "1.2.3.4",
      });
      return new Response(JSON.stringify({ success: true }));
    });
    vi.stubGlobal("fetch", fetchMock);

    const res = await verifyTurnstile("tok", "sekret", "1.2.3.4");

    expect(res).toEqual({ success: true, errorCodes: undefined });
    expect(fetchMock).toHaveBeenCalledOnce();
  });

  it("retorna sucesso false com os error codes quando o token é inválido", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(
        async () =>
          new Response(
            JSON.stringify({
              success: false,
              "error-codes": ["invalid-input-response"],
            }),
          ),
      ),
    );

    const res = await verifyTurnstile("bad-token", "sekret");

    expect(res).toEqual({
      success: false,
      errorCodes: ["invalid-input-response"],
    });
  });
});

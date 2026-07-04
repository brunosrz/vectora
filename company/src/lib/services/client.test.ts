import { describe, it, expect, vi, beforeEach } from "vitest";

import {
  SERVICES_URL,
  getSessionToken,
  setSessionCookie,
  clearSessionCookie,
  requireSessionToken,
  servicesFetch,
} from "./client";

const { mockGetCookie, mockSetCookie } = vi.hoisted(() => ({
  mockGetCookie: vi.fn<(name: string) => string | undefined>(),
  mockSetCookie: vi.fn(),
}));

vi.mock("@tanstack/react-start/server", () => ({
  getCookie: mockGetCookie,
  setCookie: mockSetCookie,
}));

const FETCH_MOCK = vi.fn();

beforeEach(() => {
  vi.stubGlobal("fetch", FETCH_MOCK);
  FETCH_MOCK.mockReset();
  mockGetCookie.mockReset();
  mockSetCookie.mockReset();
});

function mockOk(body: object): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

describe("SERVICES_URL", () => {
  it("usa o default quando SERVICES_URL não está no env", () => {
    expect(SERVICES_URL).toBe("https://services.vectora.company");
  });
});

describe("getSessionToken", () => {
  it("retorna o valor do cookie vsession", () => {
    mockGetCookie.mockReturnValue("tok_abc123");
    expect(getSessionToken()).toBe("tok_abc123");
    expect(mockGetCookie).toHaveBeenCalledWith("vsession");
  });

  it("retorna undefined quando o cookie não existe (edge)", () => {
    mockGetCookie.mockReturnValue(undefined);
    expect(getSessionToken()).toBeUndefined();
  });
});

describe("setSessionCookie", () => {
  it("seta o cookie httpOnly com a expiração informada", () => {
    setSessionCookie("tok_xyz", "2026-08-01T00:00:00.000Z");
    expect(mockSetCookie).toHaveBeenCalledWith(
      "vsession",
      "tok_xyz",
      expect.objectContaining({
        httpOnly: true,
        secure: true,
        sameSite: "lax",
        path: "/",
        expires: new Date("2026-08-01T00:00:00.000Z"),
      }),
    );
  });
});

describe("clearSessionCookie", () => {
  it("zera o cookie com maxAge 0", () => {
    clearSessionCookie();
    expect(mockSetCookie).toHaveBeenCalledWith(
      "vsession",
      "",
      expect.objectContaining({ maxAge: 0 }),
    );
  });
});

describe("requireSessionToken", () => {
  it("retorna o token quando presente", () => {
    mockGetCookie.mockReturnValue("tok_present");
    expect(requireSessionToken()).toBe("tok_present");
  });

  it("lança 'unauthorized' quando o cookie está ausente (edge)", () => {
    mockGetCookie.mockReturnValue(undefined);
    expect(() => requireSessionToken()).toThrowError("unauthorized");
  });
});

describe("servicesFetch", () => {
  it("injeta Authorization Bearer quando há sessão e retorna o body parseado", async () => {
    mockGetCookie.mockReturnValue("tok_bearer");
    FETCH_MOCK.mockResolvedValueOnce(mockOk({ ok: true }));

    const result = await servicesFetch<{ ok: boolean }>("/billing/checkout", {
      method: "POST",
    });

    expect(result).toEqual({ ok: true });
    const [url, init] = FETCH_MOCK.mock.calls[0];
    expect(url).toBe("https://services.vectora.company/billing/checkout");
    const headers = init.headers as Headers;
    expect(headers.get("Authorization")).toBe("Bearer tok_bearer");
    expect(headers.get("Content-Type")).toBe("application/json");
  });

  it("não injeta Authorization quando não há sessão (edge)", async () => {
    mockGetCookie.mockReturnValue(undefined);
    FETCH_MOCK.mockResolvedValueOnce(mockOk({ data: 1 }));

    await servicesFetch("/issues");

    const [, init] = FETCH_MOCK.mock.calls[0];
    const headers = init.headers as Headers;
    expect(headers.get("Authorization")).toBeNull();
  });

  it("lança o erro do body quando a resposta não é ok", async () => {
    mockGetCookie.mockReturnValue(undefined);
    FETCH_MOCK.mockResolvedValueOnce(
      new Response(JSON.stringify({ error: "invalid_credentials" }), {
        status: 401,
      }),
    );

    await expect(servicesFetch("/auth/login")).rejects.toThrowError(
      "invalid_credentials",
    );
  });

  it("usa fallback services_error_{status} quando o body não tem .error (edge)", async () => {
    mockGetCookie.mockReturnValue(undefined);
    FETCH_MOCK.mockResolvedValueOnce(new Response("not json", { status: 500 }));

    await expect(servicesFetch("/billing/portal")).rejects.toThrowError(
      "services_error_500",
    );
  });

  it("não quebra em resposta ok com body JSON inválido (edge)", async () => {
    mockGetCookie.mockReturnValue(undefined);
    FETCH_MOCK.mockResolvedValueOnce(new Response("not json", { status: 200 }));

    await expect(servicesFetch("/license/history")).resolves.toEqual({});
  });
});

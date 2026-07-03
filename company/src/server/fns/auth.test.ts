import { describe, it, expect, vi, beforeEach } from "vitest";

import {
  getSession,
  signUp,
  signIn,
  signOut,
  verifyEmail,
  sendMagicLink,
} from "./auth";

const {
  mockGetSessionToken,
  mockServicesFetch,
  mockSetSessionCookie,
  mockClearSessionCookie,
} = vi.hoisted(() => ({
  mockGetSessionToken: vi.fn(),
  mockServicesFetch: vi.fn(),
  mockSetSessionCookie: vi.fn(),
  mockClearSessionCookie: vi.fn(),
}));

vi.mock("#/lib/services/client", () => ({
  getSessionToken: mockGetSessionToken,
  servicesFetch: mockServicesFetch,
  setSessionCookie: mockSetSessionCookie,
  clearSessionCookie: mockClearSessionCookie,
}));

beforeEach(() => {
  vi.clearAllMocks();
});

describe("getSession", () => {
  it("retorna null sem bater na rede quando não há cookie de sessão (edge)", async () => {
    mockGetSessionToken.mockReturnValue(undefined);

    const result = await getSession();

    expect(result).toBeNull();
    expect(mockServicesFetch).not.toHaveBeenCalled();
  });

  it("retorna o usuário quando a sessão é válida", async () => {
    mockGetSessionToken.mockReturnValue("tok");
    mockServicesFetch.mockResolvedValue({
      id: "u1",
      email: "a@b.com",
      full_name: "Ana",
      country: "BR",
      language: "pt",
      email_verified: true,
    });

    const result = await getSession();

    expect(result?.email).toBe("a@b.com");
    expect(mockServicesFetch).toHaveBeenCalledWith("/auth/me");
  });

  it("retorna null quando servicesFetch lança (edge — token expirado/inválido)", async () => {
    mockGetSessionToken.mockReturnValue("tok-expirado");
    mockServicesFetch.mockRejectedValue(new Error("services_error_401"));

    await expect(getSession()).resolves.toBeNull();
  });
});

describe("signUp", () => {
  it("valida e envia o payload para /auth/signup", async () => {
    mockServicesFetch.mockResolvedValue({
      needsConfirmation: true,
      email: "new@user.com",
    });

    const result = await signUp({
      data: {
        name: "Nova Usuária",
        email: "new@user.com",
        password: "senha1234",
        turnstileToken: "tt-1",
      },
    });

    expect(result).toEqual({ needsConfirmation: true, email: "new@user.com" });
    expect(mockServicesFetch).toHaveBeenCalledWith(
      "/auth/signup",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("rejeita senha curta antes de bater na rede (edge — validação Zod)", async () => {
    await expect(
      signUp({
        data: {
          name: "Nova",
          email: "new@user.com",
          password: "curta",
          turnstileToken: "tt-1",
        },
      }),
    ).rejects.toBeTruthy();
    expect(mockServicesFetch).not.toHaveBeenCalled();
  });

  it("rejeita email inválido (edge — validação Zod)", async () => {
    await expect(
      signUp({
        data: {
          name: "Nova",
          email: "nao-e-email",
          password: "senha1234",
          turnstileToken: "tt-1",
        },
      }),
    ).rejects.toBeTruthy();
  });
});

describe("signIn", () => {
  it("seta o cookie de sessão em caso de sucesso", async () => {
    mockServicesFetch.mockResolvedValue({
      session_token: "tok-novo",
      expires_at: "2026-08-01T00:00:00.000Z",
    });

    const result = await signIn({
      data: { email: "a@b.com", password: "senha1234" },
    });

    expect(result).toEqual({ ok: true });
    expect(mockSetSessionCookie).toHaveBeenCalledWith(
      "tok-novo",
      "2026-08-01T00:00:00.000Z",
    );
  });

  it("rejeita senha vazia (edge — validação Zod)", async () => {
    await expect(
      signIn({ data: { email: "a@b.com", password: "" } }),
    ).rejects.toBeTruthy();
    expect(mockSetSessionCookie).not.toHaveBeenCalled();
  });

  it("propaga o erro de credenciais inválidas sem setar cookie (edge)", async () => {
    mockServicesFetch.mockRejectedValue(new Error("invalid_credentials"));

    await expect(
      signIn({ data: { email: "a@b.com", password: "errada123" } }),
    ).rejects.toThrowError("invalid_credentials");
    expect(mockSetSessionCookie).not.toHaveBeenCalled();
  });
});

describe("signOut", () => {
  it("chama /auth/logout e limpa o cookie quando há sessão", async () => {
    mockGetSessionToken.mockReturnValue("tok");
    mockServicesFetch.mockResolvedValue({ ok: true });

    const result = await signOut();

    expect(mockServicesFetch).toHaveBeenCalledWith(
      "/auth/logout",
      expect.objectContaining({ method: "POST" }),
    );
    expect(mockClearSessionCookie).toHaveBeenCalled();
    expect(result).toEqual({ ok: true });
  });

  it("limpa o cookie mesmo sem sessão ativa, sem chamar a rede (edge)", async () => {
    mockGetSessionToken.mockReturnValue(undefined);

    const result = await signOut();

    expect(mockServicesFetch).not.toHaveBeenCalled();
    expect(mockClearSessionCookie).toHaveBeenCalled();
    expect(result).toEqual({ ok: true });
  });

  it("limpa o cookie mesmo se o /auth/logout falhar no worker (edge — tolerante a erro)", async () => {
    mockGetSessionToken.mockReturnValue("tok");
    mockServicesFetch.mockRejectedValue(new Error("network_error"));

    const result = await signOut();

    expect(mockClearSessionCookie).toHaveBeenCalled();
    expect(result).toEqual({ ok: true });
  });
});

describe("verifyEmail", () => {
  it("seta o cookie e retorna o redirect", async () => {
    mockServicesFetch.mockResolvedValue({
      session_token: "tok-verify",
      expires_at: "2026-08-01T00:00:00.000Z",
      redirect: "/dashboard?welcome=true",
    });

    const result = await verifyEmail({ data: { token: "email-token" } });

    expect(result).toEqual({ redirect: "/dashboard?welcome=true" });
    expect(mockSetSessionCookie).toHaveBeenCalledWith(
      "tok-verify",
      "2026-08-01T00:00:00.000Z",
    );
  });

  it("rejeita token vazio (edge — validação Zod)", async () => {
    await expect(verifyEmail({ data: { token: "" } })).rejects.toBeTruthy();
  });
});

describe("sendMagicLink", () => {
  it("envia o email para /auth/magic-link", async () => {
    mockServicesFetch.mockResolvedValue({ ok: true });

    const result = await sendMagicLink({ data: { email: "a@b.com" } });

    expect(result).toEqual({ ok: true });
    expect(mockServicesFetch).toHaveBeenCalledWith(
      "/auth/magic-link",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("rejeita email inválido (edge — validação Zod)", async () => {
    await expect(
      sendMagicLink({ data: { email: "nao-e-email" } }),
    ).rejects.toBeTruthy();
    expect(mockServicesFetch).not.toHaveBeenCalled();
  });
});

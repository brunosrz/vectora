import { createServerFn } from "@tanstack/react-start";
import { z } from "zod";
import {
  clearSessionCookie,
  getSessionToken,
  servicesFetch,
  setSessionCookie,
} from "#/lib/services/client";

export interface SessionUser {
  id: string;
  email: string;
  full_name: string;
  country: "BR" | "INTL";
  language: string;
  email_verified: boolean;
  role: "user" | "admin";
}

export const getSession = createServerFn({ method: "GET" }).handler(
  async (): Promise<SessionUser | null> => {
    if (!getSessionToken()) return null;
    try {
      return await servicesFetch<SessionUser>("/auth/me");
    } catch {
      return null;
    }
  },
);

const SignUpSchema = z.object({
  name: z.string().min(2),
  email: z.string().email(),
  password: z.string().min(8),
  turnstileToken: z.string(),
});

export const signUp = createServerFn({ method: "POST" })
  .validator(SignUpSchema)
  .handler(async ({ data: input }) => {
    return servicesFetch<{ needsConfirmation: true; email: string }>(
      "/auth/signup",
      { method: "POST", body: JSON.stringify(input) },
    );
  });

const SignInSchema = z.object({
  email: z.string().email(),
  password: z.string().min(1),
});

export const signIn = createServerFn({ method: "POST" })
  .validator(SignInSchema)
  .handler(async ({ data: input }) => {
    const res = await servicesFetch<{
      session_token: string;
      expires_at: string;
    }>("/auth/login", { method: "POST", body: JSON.stringify(input) });
    setSessionCookie(res.session_token, res.expires_at);
    return { ok: true };
  });

export const signOut = createServerFn({ method: "POST" }).handler(async () => {
  if (getSessionToken()) {
    await servicesFetch("/auth/logout", { method: "POST" }).catch(
      () => undefined,
    );
  }
  clearSessionCookie();
  return { ok: true };
});

// Link de /auth/verify?token=... (email de confirmação ou magic link — mesmo
// endpoint em services, `purpose` já resolvido lá).
export const verifyEmail = createServerFn({ method: "POST" })
  .validator(z.object({ token: z.string().min(1) }))
  .handler(async ({ data }) => {
    const res = await servicesFetch<{
      session_token: string;
      expires_at: string;
      redirect: string;
    }>("/auth/verify", { method: "POST", body: JSON.stringify(data) });
    setSessionCookie(res.session_token, res.expires_at);
    return { redirect: res.redirect };
  });

export const sendMagicLink = createServerFn({ method: "POST" })
  .validator(z.object({ email: z.string().email() }))
  .handler(async ({ data }) => {
    await servicesFetch("/auth/magic-link", {
      method: "POST",
      body: JSON.stringify(data),
    });
    return { ok: true };
  });

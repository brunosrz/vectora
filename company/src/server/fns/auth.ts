import { createServerFn } from "@tanstack/react-start";
import { z } from "zod";
import { createElement } from "react";
import { render } from "@react-email/render";
import { createSupabaseServerClient } from "#/lib/supabase/server";
import { verifyTurnstile } from "#/lib/turnstile";
import { resend, FROM_EMAIL } from "#/lib/email/resend";
import WelcomeEmail from "../../../emails/welcome";

export const getSession = createServerFn({ method: "GET" }).handler(
  async () => {
    const supabase = createSupabaseServerClient();
    const { data } = await supabase.auth.getUser();
    return data.user ?? null;
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
    const turnstile = await verifyTurnstile(input.turnstileToken);
    if (!turnstile.success) throw new Error("turnstile_failed");

    const supabase = createSupabaseServerClient();
    const appUrl = process.env.APP_URL ?? "https://vectora.company";
    const { data, error } = await supabase.auth.signUp({
      email: input.email,
      password: input.password,
      options: {
        data: { full_name: input.name },
        // Após clicar no link de confirmação, o Supabase redireciona para cá
        // com `?code=...`; a rota /auth/callback troca por sessão → /dashboard.
        emailRedirectTo: `${appUrl}/auth/callback`,
      },
    });
    if (error) throw new Error(error.message);

    // Confirmação de email ligada → signUp NÃO retorna sessão até o usuário
    // clicar no link. Sem isto o front ia pro /dashboard, que sem sessão volta
    // pro login e parece que "não criou conta". O front mostra "confirme o email".
    if (!data.session) {
      return { needsConfirmation: true as const, email: input.email };
    }

    // Sessão imediata (confirmação desligada): manda o welcome e vai pro dashboard.
    const trialEndsAt = new Date(
      Date.now() + 30 * 24 * 60 * 60 * 1000,
    ).toLocaleDateString("pt-BR", {
      day: "2-digit",
      month: "long",
      year: "numeric",
    });

    try {
      const html = await render(
        createElement(WelcomeEmail, { name: input.name, trialEndsAt }),
      );
      await resend.emails.send({
        from: FROM_EMAIL,
        to: input.email,
        subject: "Seu Vectora está pronto — trial de 30 dias ativo",
        html,
      });
    } catch {
      // Non-blocking: email failure does not abort signup
    }

    return {
      needsConfirmation: false as const,
      redirect: "/dashboard?welcome=true",
    };
  });

const SignInSchema = z.object({
  email: z.string().email(),
  password: z.string().min(1),
});

export const signIn = createServerFn({ method: "POST" })
  .validator(SignInSchema)
  .handler(async ({ data: input }) => {
    const supabase = createSupabaseServerClient();
    const { error } = await supabase.auth.signInWithPassword({
      email: input.email,
      password: input.password,
    });
    if (error) throw new Error(error.message);
    return { ok: true };
  });

export const signOut = createServerFn({ method: "POST" }).handler(async () => {
  const supabase = createSupabaseServerClient();
  await supabase.auth.signOut();
  return { ok: true };
});

export const exchangeOAuthCode = createServerFn({ method: "POST" })
  .validator(z.object({ code: z.string() }))
  .handler(async ({ data }) => {
    const supabase = createSupabaseServerClient();
    const { error } = await supabase.auth.exchangeCodeForSession(data.code);
    if (error) throw new Error(error.message);
    return { ok: true };
  });

export const sendMagicLink = createServerFn({ method: "POST" })
  .validator(z.object({ email: z.string().email() }))
  .handler(async ({ data }) => {
    const supabase = createSupabaseServerClient();
    const { error } = await supabase.auth.signInWithOtp({ email: data.email });
    if (error) throw new Error(error.message);
    return { ok: true };
  });

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
    const { error } = await supabase.auth.signUp({
      email: input.email,
      password: input.password,
      options: { data: { full_name: input.name } },
    });
    if (error) throw new Error(error.message);

    const trialEndsAt = new Date(
      Date.now() + 30 * 24 * 60 * 60 * 1000,
    ).toLocaleDateString("pt-BR", {
      day: "2-digit",
      month: "long",
      year: "numeric",
    });

    const html = await render(
      createElement(WelcomeEmail, { name: input.name, trialEndsAt }),
    );
    await resend.emails
      .send({
        from: FROM_EMAIL,
        to: input.email,
        subject: "Seu Vectora está pronto — trial de 30 dias ativo",
        html,
      })
      .catch(() => {
        // Non-blocking: if email fails, signup still succeeds
      });

    return { redirect: "/dashboard?welcome=true" };
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

export const sendMagicLink = createServerFn({ method: "POST" })
  .validator(z.object({ email: z.string().email() }))
  .handler(async ({ data }) => {
    const supabase = createSupabaseServerClient();
    const { error } = await supabase.auth.signInWithOtp({ email: data.email });
    if (error) throw new Error(error.message);
    return { ok: true };
  });

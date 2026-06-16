import { createServerFn } from "@tanstack/react-start";
import { z } from "zod";
import { createSupabaseAdminClient } from "#/lib/supabase/admin";
import { verifyTurnstile } from "#/lib/turnstile";
import { resend, SUPPORT_EMAIL, FROM_EMAIL } from "#/lib/email/resend";

const IssueSchema = z.object({
  title: z.string().min(3).max(200),
  category: z.enum(["bug", "feedback", "feature"]),
  description: z.string().max(5000).optional(),
  email: z.string().email().optional().or(z.literal("")),
  turnstileToken: z.string(),
});

export const submitIssue = createServerFn({ method: "POST" })
  .validator(IssueSchema)
  .handler(async ({ data: input }) => {
    const turnstile = await verifyTurnstile(input.turnstileToken);
    if (!turnstile.success) throw new Error("turnstile_failed");

    const admin = createSupabaseAdminClient();
    const { error } = await admin.from("issues").insert({
      title: input.title,
      category: input.category,
      description: input.description ?? null,
      email: input.email || null,
    } as never);
    if (error) throw new Error(error.message);

    await resend.emails.send({
      from: FROM_EMAIL,
      to: SUPPORT_EMAIL,
      subject: `[${input.category.toUpperCase()}] ${input.title}`,
      html: `
        <p><strong>Categoria:</strong> ${input.category}</p>
        <p><strong>Título:</strong> ${input.title}</p>
        <p><strong>Descrição:</strong> ${input.description ?? "—"}</p>
        <p><strong>Email:</strong> ${input.email ?? "—"}</p>
      `,
    });

    return { ok: true };
  });

export type IssueListItem = {
  id: string;
  title: string;
  category: "bug" | "feedback" | "feature";
  description: string | null;
  created_at: string;
};

// Lista pública das issues abertas. NUNCA seleciona `email` (privacidade do
// reporter). RLS nega acesso de cliente, então usa o admin client server-side.
export const listOpenIssues = createServerFn({ method: "GET" }).handler(
  async (): Promise<IssueListItem[]> => {
    const admin = createSupabaseAdminClient();
    const { data, error } = await admin
      .from("issues")
      .select("id, title, category, description, created_at")
      .order("created_at", { ascending: false })
      .limit(100);
    if (error) throw new Error(error.message);
    return data;
  },
);

export const joinWaitlist = createServerFn({ method: "POST" })
  .validator(
    z.object({
      email: z.string().email(),
      turnstileToken: z.string(),
      source: z.string().optional(),
    }),
  )
  .handler(async ({ data: input }) => {
    const turnstile = await verifyTurnstile(input.turnstileToken);
    if (!turnstile.success) throw new Error("turnstile_failed");

    const { addToWaitlist } = await import("#/lib/leads");
    await addToWaitlist({ email: input.email, source: input.source });
    return { ok: true };
  });

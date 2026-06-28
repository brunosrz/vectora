import { createServerFn } from "@tanstack/react-start";
import { z } from "zod";
import { createSupabaseServerClient } from "#/lib/supabase/server";
import { createSupabaseAdminClient } from "#/lib/supabase/admin";

async function getUid(): Promise<string> {
  const supabase = createSupabaseServerClient();
  const { data } = await supabase.auth.getUser();
  if (!data.user) throw new Error("unauthorized");
  return data.user.id;
}

const RELAY_URL =
  (process.env.RELAY_URL as string | undefined) ?? "https://relay.vectora.chat";

export const authorizeDevice = createServerFn({ method: "POST" })
  .validator(z.object({ state: z.string().min(1) }))
  .handler(async ({ data: input }) => {
    const uid = await getUid();

    const admin = createSupabaseAdminClient();
    const { data, error } = await admin
      .from("tokens")
      .select("token")
      .eq("user_id", uid)
      .single();

    if (error) throw new Error("token_fetch_failed");
    const row = data as { token: string | null } | null;
    if (!row?.token) throw new Error("no_token");

    const secret = process.env.RELAY_OAUTH_SECRET;
    if (!secret) throw new Error("oauth_not_configured");

    const resp = await fetch(`${RELAY_URL}/oauth/token`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${secret}`,
      },
      body: JSON.stringify({ state: input.state, token: row.token }),
    });

    if (!resp.ok) throw new Error("relay_error");
    return { ok: true };
  });

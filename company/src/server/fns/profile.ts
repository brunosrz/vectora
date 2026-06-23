import { createServerFn } from "@tanstack/react-start";
import { z } from "zod";
import { createSupabaseServerClient } from "#/lib/supabase/server";

async function getUid() {
  const supabase = createSupabaseServerClient();
  const { data } = await supabase.auth.getUser();
  if (!data.user) throw new Error("unauthorized");
  return data.user.id;
}

export const updateProfile = createServerFn({ method: "POST" })
  .validator(
    z.object({
      full_name: z.string().min(2).max(100).optional(),
      country: z.enum(["BR", "INTL"]).optional(),
      language: z.string().min(2).max(10).optional(),
    }),
  )
  .handler(async ({ data: input }) => {
    const uid = await getUid();
    const supabase = createSupabaseServerClient();
    const patch: Record<string, unknown> = {
      updated_at: new Date().toISOString(),
    };
    if (input.full_name !== undefined) patch.full_name = input.full_name;
    if (input.country !== undefined) patch.country = input.country;
    if (input.language !== undefined) patch.language = input.language;
    const { error } = await (supabase.from("profiles") as any)
      .update(patch)
      .eq("id", uid);
    if (error) throw new Error((error as { message: string }).message);
    return { ok: true };
  });

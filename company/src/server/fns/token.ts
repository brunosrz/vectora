import { createServerFn } from "@tanstack/react-start";
import { createSupabaseAdminClient } from "#/lib/supabase/admin";
import { createSupabaseServerClient } from "#/lib/supabase/server";

async function getUid() {
  const supabase = createSupabaseServerClient();
  const { data } = await supabase.auth.getUser();
  if (!data.user) throw new Error("unauthorized");
  return data.user.id;
}

export const getTokenStatus = createServerFn({ method: "GET" }).handler(
  async () => {
    const uid = await getUid();
    const admin = createSupabaseAdminClient();
    const { data, error } = await admin
      .from("tokens")
      .select("token")
      .eq("user_id", uid)
      .single();
    if (error) throw new Error(error.message);
    const row = data as { token: string | null } | null;
    return { revealed: row?.token === null };
  },
);

export const getToken = createServerFn({ method: "POST" }).handler(async () => {
  const uid = await getUid();
  const admin = createSupabaseAdminClient();

  const { data, error } = await admin
    .from("tokens")
    .select("token")
    .eq("user_id", uid)
    .single();

  if (error) throw new Error(error.message);
  const row = data as { token: string | null } | null;
  if (!row || row.token === null) return { revealed: true, token: null };

  await (admin.from("tokens") as any)
    .update({ token: null })
    .eq("user_id", uid);

  return { revealed: false, token: row.token };
});

export const rotateToken = createServerFn({ method: "POST" }).handler(
  async () => {
    const uid = await getUid();
    const admin = createSupabaseAdminClient();

    const { data, error } = await admin.functions.invoke("rotate-token", {
      body: { user_id: uid },
    });
    if (error) throw new Error(error.message);

    return data as { token: string };
  },
);

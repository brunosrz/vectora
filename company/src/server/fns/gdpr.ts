import { createServerFn } from "@tanstack/react-start";
import { createElement } from "react";
import { render } from "@react-email/render";
import { createSupabaseServerClient } from "#/lib/supabase/server";
import { createSupabaseAdminClient } from "#/lib/supabase/admin";
import { resend, FROM_EMAIL } from "#/lib/email/resend";
import AccountDeleted from "../../../emails/account-deleted";

async function getUser() {
  const supabase = createSupabaseServerClient();
  const { data } = await supabase.auth.getUser();
  if (!data.user) throw new Error("unauthorized");
  return data.user;
}

export const exportData = createServerFn({ method: "POST" }).handler(
  async () => {
    const user = await getUser();
    const admin = createSupabaseAdminClient();

    const [profiles, subscriptions, licenseChecks, apiKeys] = await Promise.all(
      [
        admin.from("profiles").select("*").eq("id", user.id).single(),
        admin.from("subscriptions").select("*").eq("user_id", user.id),
        admin.from("license_checks").select("*").eq("user_id", user.id),
        admin
          .from("api_keys")
          .select("id, name, scopes, created_at, last_used_at")
          .eq("user_id", user.id),
      ],
    );

    const exportPayload = JSON.stringify(
      {
        profile: profiles.data,
        subscriptions: subscriptions.data,
        license_checks: licenseChecks.data,
        api_keys: apiKeys.data,
        exported_at: new Date().toISOString(),
      },
      null,
      2,
    );

    const filename = `vectora-export-${user.id}-${Date.now()}.json`;
    const { error: uploadError } = await admin.storage
      .from("exports")
      .upload(
        filename,
        new Blob([exportPayload], { type: "application/json" }),
        {
          contentType: "application/json",
        },
      );
    if (uploadError) throw new Error(uploadError.message);

    const { data: signedUrl, error: urlError } = await admin.storage
      .from("exports")
      .createSignedUrl(filename, 300);
    if (urlError) throw new Error(urlError.message);

    return { url: signedUrl.signedUrl };
  },
);

export const requestAccountDeletion = createServerFn({
  method: "POST",
}).handler(async () => {
  const user = await getUser();
  const admin = createSupabaseAdminClient();

  const deletionDate = new Date(
    Date.now() + 30 * 24 * 60 * 60 * 1000,
  ).toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "long",
    year: "numeric",
  });
  const html = await render(
    createElement(AccountDeleted, {
      name: (user.user_metadata.full_name as string | undefined) ?? user.email!,
      deletionDate,
    }),
  );
  await resend.emails.send({
    from: FROM_EMAIL,
    to: user.email!,
    subject: "Conta Vectora agendada para exclusão",
    html,
  });

  await admin
    .from("profiles")
    .update({ soft_delete_at: new Date().toISOString() } as never)
    .eq("id", user.id);

  const supabase = createSupabaseServerClient();
  await supabase.auth.signOut();

  return { ok: true };
});

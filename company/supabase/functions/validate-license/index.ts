import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

Deno.serve(async (req) => {
  if (req.method !== "POST") {
    return new Response(
      JSON.stringify({ valid: false, error: "Method not allowed" }),
      { status: 405 },
    );
  }

  const body = await req.json().catch(() => ({}));
  const token: string | undefined = body.token;
  const version: string | undefined = body.version ?? "unknown";

  if (!token) {
    return new Response(
      JSON.stringify({ valid: false, error: "token_required" }),
      { status: 400 },
    );
  }

  const admin = createClient(
    Deno.env.get("SUPABASE_URL")!,
    Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!,
  );

  // Hash the incoming token to compare
  const hashBytes = await crypto.subtle.digest(
    "SHA-256",
    new TextEncoder().encode(token),
  );
  const tokenHash = Array.from(new Uint8Array(hashBytes))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");

  // Look up by hash
  const { data: tokenRow } = await admin
    .from("tokens")
    .select("user_id")
    .eq("token_hash", tokenHash)
    .single();

  if (!tokenRow) {
    return new Response(JSON.stringify({ valid: false, reason: "not_found" }), {
      status: 200,
    });
  }

  const uid = tokenRow.user_id;

  // Check subscription status
  const { data: sub } = await admin
    .from("subscriptions")
    .select("status, tier, trial_ends_at, current_period_end")
    .eq("user_id", uid)
    .single();

  let result: "valid" | "invalid" | "expired" | "not_found" = "invalid";

  if (sub) {
    const now = new Date();
    if (sub.status === "active") {
      result = "valid";
    } else if (sub.status === "trialing") {
      result = new Date(sub.trial_ends_at) > now ? "valid" : "expired";
    } else if (sub.status === "past_due") {
      result = "valid"; // grace period
    } else {
      result = "expired";
    }
  }

  // Record license check
  const ip = req.headers.get("x-forwarded-for")?.split(",")[0].trim() ?? "";
  await admin.from("license_checks").insert({
    user_id: uid,
    vectora_version: version,
    result,
    ip,
  });

  return new Response(
    JSON.stringify({
      valid: result === "valid",
      reason: result,
      tier: sub?.tier ?? null,
    }),
    { headers: { "Content-Type": "application/json" } },
  );
});

import { createClient } from "https://esm.sh/@supabase/supabase-js@2";
import Stripe from "https://esm.sh/stripe@14";

Deno.serve(async (req) => {
  if (req.method !== "POST") {
    return new Response(JSON.stringify({ error: "Method not allowed" }), {
      status: 405,
    });
  }

  const authHeader = req.headers.get("Authorization");
  if (!authHeader) {
    return new Response(JSON.stringify({ error: "Unauthorized" }), {
      status: 401,
    });
  }

  const supabaseUrl = Deno.env.get("SUPABASE_URL")!;
  const serviceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
  const appUrl = Deno.env.get("APP_URL") ?? "https://app.vectora.company";

  const anonClient = createClient(
    supabaseUrl,
    Deno.env.get("SUPABASE_ANON_KEY")!,
    {
      global: { headers: { Authorization: authHeader } },
    },
  );
  const {
    data: { user },
  } = await anonClient.auth.getUser();
  if (!user)
    return new Response(JSON.stringify({ error: "Unauthorized" }), {
      status: 401,
    });

  const admin = createClient(supabaseUrl, serviceKey);
  const { data: sub } = await admin
    .from("subscriptions")
    .select("customer_id, currency")
    .eq("user_id", user.id)
    .single();

  if (!sub?.customer_id) {
    return new Response(JSON.stringify({ error: "No customer found" }), {
      status: 404,
    });
  }

  if (sub.currency === "BRL") {
    // Asaas doesn't have a customer portal — redirect to billing page
    const asaasBase =
      Deno.env.get("ASAAS_API_URL") ?? "https://api.asaas.com/v3";
    const asaasKey = Deno.env.get("ASAAS_API_KEY")!;

    const customerRes = await fetch(
      `${asaasBase}/customers/${sub.customer_id}`,
      {
        headers: { access_token: asaasKey },
      },
    );
    const customer = await customerRes.json();

    return new Response(
      JSON.stringify({
        url: customer.billingInfoUrl ?? `${appUrl}/dashboard/billing`,
      }),
      { headers: { "Content-Type": "application/json" } },
    );
  }

  // Stripe portal
  const stripe = new Stripe(Deno.env.get("STRIPE_SECRET_KEY")!, {
    apiVersion: "2024-12-18.acacia",
  });
  const portal = await stripe.billingPortal.sessions.create({
    customer: sub.customer_id,
    return_url: `${appUrl}/dashboard/billing`,
  });

  return new Response(JSON.stringify({ url: portal.url }), {
    headers: { "Content-Type": "application/json" },
  });
});

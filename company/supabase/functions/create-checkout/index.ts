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

  // Free não passa por checkout (sem conta, sem cobrança) — este endpoint só
  // existe pra assinar Pro.
  const country: "BR" | "INTL" = (await req.json()).country ?? "INTL";
  const plan = "pro" as const;

  const admin = createClient(supabaseUrl, serviceKey);

  if (country === "INTL") {
    // Stripe
    const stripe = new Stripe(Deno.env.get("STRIPE_SECRET_KEY")!, {
      apiVersion: "2024-12-18.acacia",
    });

    const priceId = Deno.env.get("STRIPE_PRICE_PRO_USD")!;

    const { data: sub } = await admin
      .from("subscriptions")
      .select("customer_id")
      .eq("user_id", user.id)
      .single();

    let customerId = sub?.customer_id;
    if (!customerId) {
      const customer = await stripe.customers.create({
        email: user.email,
        metadata: { user_id: user.id },
      });
      customerId = customer.id;
      await admin
        .from("subscriptions")
        .update({ customer_id: customerId })
        .eq("user_id", user.id);
    }

    const session = await stripe.checkout.sessions.create({
      customer: customerId,
      mode: "subscription",
      line_items: [{ price: priceId, quantity: 1 }],
      success_url: `${appUrl}/dashboard/billing?success=1`,
      cancel_url: `${appUrl}/dashboard/billing`,
      metadata: { user_id: user.id, plan },
    });

    return new Response(JSON.stringify({ url: session.url }), {
      headers: { "Content-Type": "application/json" },
    });
  }

  // Asaas (BR)
  const asaasKey = Deno.env.get("ASAAS_API_KEY")!;
  const asaasBase = Deno.env.get("ASAAS_API_URL") ?? "https://api.asaas.com/v3";

  const amount = 24.0;

  const paymentRes = await fetch(`${asaasBase}/payments`, {
    method: "POST",
    headers: { access_token: asaasKey, "Content-Type": "application/json" },
    body: JSON.stringify({
      customer: user.email,
      billingType: "UNDEFINED",
      value: amount,
      dueDate: new Date(Date.now() + 86_400_000).toISOString().split("T")[0],
      description: "Vectora Pro — 1 mês",
      externalReference: `${user.id}:${plan}`,
    }),
  });

  const payment = await paymentRes.json();
  const checkoutUrl =
    payment.invoiceUrl ?? payment.bankSlipUrl ?? `${appUrl}/dashboard/billing`;

  return new Response(JSON.stringify({ url: checkoutUrl }), {
    headers: { "Content-Type": "application/json" },
  });
});

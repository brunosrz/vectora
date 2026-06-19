import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'
import Stripe from 'https://esm.sh/stripe@14'
import { Resend } from 'https://esm.sh/resend@4'

const admin = createClient(
  Deno.env.get('SUPABASE_URL')!,
  Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!,
)
const resend = new Resend(Deno.env.get('RESEND_API_KEY')!)
const FROM_EMAIL = 'noreply@vectora.company'

async function getUserEmail(uid: string): Promise<string | null> {
  const { data } = await admin.auth.admin.getUserById(uid)
  return data.user?.email ?? null
}

function invoicePaidHtml(
  name: string,
  amount: string,
  plan: string,
  periodEnd: string,
): string {
  return `<div style="background:#0a0e1a;font-family:monospace;padding:32px 24px;max-width:560px;margin:0 auto">
    <h1 style="color:#fff;font-size:22px;font-weight:700">Vectora</h1>
    <p style="color:#4ade80;font-size:14px;font-weight:600">✓ Pagamento confirmado</p>
    <p style="color:#94a3b8;font-size:14px">Olá, ${name}! Recebemos seu pagamento de <strong>${amount}</strong> para o plano <strong>${plan}</strong>. Acesso ativo até ${periodEnd}.</p>
    <hr style="border-color:#1e293b;margin:24px 0"><p style="color:#475569;font-size:12px">Vectora · vectora.company</p>
  </div>`
}

function invoiceFailedHtml(name: string, amount: string): string {
  return `<div style="background:#0a0e1a;font-family:monospace;padding:32px 24px;max-width:560px;margin:0 auto">
    <h1 style="color:#fff;font-size:22px;font-weight:700">Vectora</h1>
    <p style="color:#f87171;font-size:14px;font-weight:600">⚠ Falha no pagamento</p>
    <p style="color:#94a3b8;font-size:14px">Olá, ${name}! Não conseguimos processar o pagamento de <strong>${amount}</strong>. Atualize seu método de pagamento para evitar a suspensão do acesso.</p>
    <a href="https://vectora.company/dashboard/billing" style="display:inline-block;background:#f87171;color:#fff;padding:12px 24px;border-radius:12px;text-decoration:none;font-size:14px;font-weight:600;margin:16px 0">Atualizar pagamento →</a>
    <hr style="border-color:#1e293b;margin:24px 0"><p style="color:#475569;font-size:12px">Vectora · vectora.company</p>
  </div>`
}

async function handleStripe(req: Request): Promise<Response> {
  const stripe = new Stripe(Deno.env.get('STRIPE_SECRET_KEY')!, {
    apiVersion: '2024-12-18.acacia',
  })
  const sig = req.headers.get('stripe-signature')
  const body = await req.text()

  let event: Stripe.Event
  try {
    event = stripe.webhooks.constructEvent(
      body,
      sig!,
      Deno.env.get('STRIPE_WEBHOOK_SECRET')!,
    )
  } catch {
    return new Response('Webhook signature failed', { status: 400 })
  }

  const uid = (event.data.object as { metadata?: { user_id?: string } })
    ?.metadata?.user_id

  await admin.from('payment_events').insert({
    user_id: uid ?? null,
    provider: 'stripe',
    event_type: event.type,
    payload: event.data.object,
    processed_at: new Date().toISOString(),
  })

  if (event.type === 'invoice.paid' && uid) {
    const inv = event.data.object as Stripe.Invoice
    const sub = await stripe.subscriptions.retrieve(inv.subscription as string)
    const plan =
      sub.metadata?.plan ?? sub.items.data[0]?.price?.metadata?.plan ?? 'plus'
    const periodEnd = new Date(
      sub.current_period_end * 1000,
    ).toLocaleDateString('pt-BR', {
      day: '2-digit',
      month: 'long',
      year: 'numeric',
    })
    await admin
      .from('subscriptions')
      .update({
        status: 'active',
        tier: plan,
        provider: 'stripe',
        provider_id: inv.subscription as string,
        current_period_end: new Date(
          sub.current_period_end * 1000,
        ).toISOString(),
      })
      .eq('user_id', uid)

    const email = await getUserEmail(uid)
    if (email) {
      const amount = (inv.amount_paid / 100).toLocaleString('en-US', {
        style: 'currency',
        currency: inv.currency.toUpperCase(),
      })
      await resend.emails.send({
        from: FROM_EMAIL,
        to: email,
        subject: 'Pagamento confirmado — Vectora',
        html: invoicePaidHtml(email, amount, plan, periodEnd),
      })
    }
  }

  if (event.type === 'invoice.payment_failed' && uid) {
    const inv = event.data.object as Stripe.Invoice
    await admin
      .from('subscriptions')
      .update({ status: 'past_due' })
      .eq('user_id', uid)

    const email = await getUserEmail(uid)
    if (email) {
      const amount = (inv.amount_due / 100).toLocaleString('en-US', {
        style: 'currency',
        currency: inv.currency.toUpperCase(),
      })
      await resend.emails.send({
        from: FROM_EMAIL,
        to: email,
        subject: 'Falha no pagamento — Vectora',
        html: invoiceFailedHtml(email, amount),
      })
    }
  }

  if (event.type === 'customer.subscription.deleted' && uid) {
    await admin
      .from('subscriptions')
      .update({
        status: 'canceled',
        canceled_at: new Date().toISOString(),
      })
      .eq('user_id', uid)
  }

  return new Response(JSON.stringify({ ok: true }), { status: 200 })
}

async function handleAsaas(req: Request): Promise<Response> {
  const body = await req.json()
  const externalRef: string = body.payment?.externalReference ?? ''
  const [uid, plan] = externalRef.split(':')
  const event = body.event as string

  await admin.from('payment_events').insert({
    user_id: uid ?? null,
    provider: 'asaas',
    event_type: event,
    payload: body,
    processed_at: new Date().toISOString(),
  })

  if ((event === 'PAYMENT_RECEIVED' || event === 'PAYMENT_CONFIRMED') && uid) {
    await admin
      .from('subscriptions')
      .update({
        status: 'active',
        tier: (plan as 'plus' | 'pro') ?? 'plus',
        provider: 'asaas',
        provider_id: body.payment?.id,
      })
      .eq('user_id', uid)

    const email = await getUserEmail(uid)
    if (email) {
      const amount = `R$${((body.payment?.value ?? 0) as number).toFixed(2).replace('.', ',')}`
      const periodEnd = new Date(
        Date.now() + 30 * 24 * 60 * 60 * 1000,
      ).toLocaleDateString('pt-BR', {
        day: '2-digit',
        month: 'long',
        year: 'numeric',
      })
      await resend.emails.send({
        from: FROM_EMAIL,
        to: email,
        subject: 'Pagamento confirmado — Vectora',
        html: invoicePaidHtml(
          email,
          amount,
          (plan as string) ?? 'Plus',
          periodEnd,
        ),
      })
    }
  }

  if (event === 'PAYMENT_OVERDUE' && uid) {
    await admin
      .from('subscriptions')
      .update({ status: 'past_due' })
      .eq('user_id', uid)

    const email = await getUserEmail(uid)
    if (email) {
      const amount = `R$${((body.payment?.value ?? 0) as number).toFixed(2).replace('.', ',')}`
      await resend.emails.send({
        from: FROM_EMAIL,
        to: email,
        subject: 'Falha no pagamento — Vectora',
        html: invoiceFailedHtml(email, amount),
      })
    }
  }

  if (event === 'PAYMENT_DELETED' || event === 'PAYMENT_REFUNDED') {
    await admin
      .from('subscriptions')
      .update({ status: 'canceled' })
      .eq('user_id', uid)
  }

  return new Response(JSON.stringify({ ok: true }), { status: 200 })
}

Deno.serve(async (req) => {
  if (req.method !== 'POST') {
    return new Response('Method not allowed', { status: 405 })
  }

  const url = new URL(req.url)
  const provider = url.searchParams.get('provider')

  if (provider === 'stripe') return handleStripe(req)
  if (provider === 'asaas') return handleAsaas(req)

  return new Response('Unknown provider', { status: 400 })
})

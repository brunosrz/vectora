import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'
import Stripe from 'https://esm.sh/stripe@14'

const admin = createClient(
  Deno.env.get('SUPABASE_URL')!,
  Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!,
)

Deno.serve(async (req) => {
  // This function should be called via pg_cron or a scheduled job
  // Requires: Authorization: Bearer <CRON_SECRET>
  const cronSecret = Deno.env.get('CRON_SECRET')
  const auth = req.headers.get('Authorization')
  if (cronSecret && auth !== `Bearer ${cronSecret}`) {
    return new Response('Unauthorized', { status: 401 })
  }

  // Find users scheduled for hard deletion (soft_delete_at > 30 days ago)
  const { data: usersToDelete } = await admin
    .from('profiles')
    .select('id')
    .not('soft_delete_at', 'is', null)
    .lt('soft_delete_at', new Date(Date.now() - 30 * 86_400_000).toISOString())

  if (!usersToDelete?.length) {
    return new Response(JSON.stringify({ deleted: 0 }), { status: 200 })
  }

  const deleted: string[] = []

  for (const { id: uid } of usersToDelete) {
    try {
      // 1. Cancel Stripe subscription if exists
      const { data: sub } = await admin
        .from('subscriptions')
        .select('provider, customer_id, provider_id')
        .eq('user_id', uid)
        .single()

      if (sub?.provider === 'stripe' && sub.provider_id) {
        const stripe = new Stripe(Deno.env.get('STRIPE_SECRET_KEY')!, {
          apiVersion: '2024-12-18.acacia',
        })
        await stripe.subscriptions.cancel(sub.provider_id).catch(() => null)
      }

      if (sub?.provider === 'asaas' && sub.customer_id) {
        const asaasBase =
          Deno.env.get('ASAAS_API_URL') ?? 'https://api.asaas.com/v3'
        await fetch(`${asaasBase}/customers/${sub.customer_id}`, {
          method: 'DELETE',
          headers: { access_token: Deno.env.get('ASAAS_API_KEY')! },
        }).catch(() => null)
      }

      // 2. Delete from auth.users — cascades to all tables
      await admin.auth.admin.deleteUser(uid)
      deleted.push(uid)
    } catch (err) {
      console.error(`Failed to delete user ${uid}:`, err)
    }
  }

  return new Response(
    JSON.stringify({ deleted: deleted.length, ids: deleted }),
    {
      headers: { 'Content-Type': 'application/json' },
    },
  )
})

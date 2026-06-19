import { createServerFn } from '@tanstack/react-start'
import { z } from 'zod'
import { createSupabaseServerClient } from '#/lib/supabase/server'
import { createSupabaseAdminClient } from '#/lib/supabase/admin'
import type { Tables } from '#/lib/supabase/types'

async function getUid() {
  const supabase = createSupabaseServerClient()
  const { data } = await supabase.auth.getUser()
  if (!data.user) throw new Error('unauthorized')
  return data.user.id
}

export const getSubscription = createServerFn({ method: 'GET' }).handler(
  async () => {
    const uid = await getUid()
    const supabase = createSupabaseServerClient()
    const { data, error } = await (supabase.from('subscriptions') as any)
      .select('*')
      .eq('user_id', uid)
      .single()
    if (error) throw new Error((error as { message: string }).message)
    return data as Tables<'subscriptions'> | null
  },
)

export const createCheckout = createServerFn({ method: 'POST' })
  .validator(z.object({ plan: z.enum(['plus', 'pro']) }))
  .handler(async ({ data: input }) => {
    const uid = await getUid()
    const admin = createSupabaseAdminClient()

    const sub = await getSubscription()
    const country = sub?.currency === 'BRL' ? 'BR' : 'INTL'

    const { data, error } = await admin.functions.invoke('create-checkout', {
      body: { plan: input.plan, country, user_id: uid },
    })
    if (error) throw new Error(error.message)
    return data as { url: string }
  })

export const createPortal = createServerFn({ method: 'POST' }).handler(
  async () => {
    const uid = await getUid()
    const admin = createSupabaseAdminClient()
    const { data, error } = await admin.functions.invoke('create-portal', {
      body: { user_id: uid },
    })
    if (error) throw new Error(error.message)
    return data as { url: string }
  },
)

export const getLicenseHistory = createServerFn({ method: 'GET' }).handler(
  async () => {
    const uid = await getUid()
    const supabase = createSupabaseServerClient()
    const { data, error } = await supabase
      .from('license_checks')
      .select('*')
      .eq('user_id', uid)
      .order('checked_at', { ascending: false })
      .limit(20)
    if (error) throw new Error(error.message)
    return data
  },
)

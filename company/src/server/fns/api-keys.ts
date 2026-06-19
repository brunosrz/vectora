import { createServerFn } from '@tanstack/react-start'
import { z } from 'zod'
import { createSupabaseServerClient } from '#/lib/supabase/server'
import { createSupabaseAdminClient } from '#/lib/supabase/admin'

async function getUid() {
  const supabase = createSupabaseServerClient()
  const { data } = await supabase.auth.getUser()
  if (!data.user) throw new Error('unauthorized')
  return data.user.id
}

async function sha256(input: string) {
  const buf = await crypto.subtle.digest(
    'SHA-256',
    new TextEncoder().encode(input),
  )
  return Array.from(new Uint8Array(buf))
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('')
}

export const listApiKeys = createServerFn({ method: 'GET' }).handler(
  async () => {
    const uid = await getUid()
    const supabase = createSupabaseServerClient()
    const { data, error } = await supabase
      .from('api_keys')
      .select('id, name, scopes, created_at, last_used_at')
      .eq('user_id', uid)
      .order('created_at', { ascending: false })
    if (error) throw new Error(error.message)
    return data
  },
)

export const createApiKey = createServerFn({ method: 'POST' })
  .validator(
    z.object({
      name: z.string().min(1).max(64),
      scopes: z.array(z.enum(['read', 'write', 'admin'])),
    }),
  )
  .handler(async ({ data: input }) => {
    const uid = await getUid()
    const admin = createSupabaseAdminClient()

    const raw = crypto.randomUUID()
    const hash = await sha256(raw)

    const { error } = await (admin.from('api_keys') as any).insert({
      user_id: uid,
      name: input.name,
      scopes: input.scopes,
      key_hash: hash,
    })
    if (error) throw new Error(error.message)

    return { secret: `vk_${raw}` }
  })

export const revokeApiKey = createServerFn({ method: 'POST' })
  .validator(z.object({ id: z.string().uuid() }))
  .handler(async ({ data: input }) => {
    const uid = await getUid()
    const supabase = createSupabaseServerClient()
    const { error } = await supabase
      .from('api_keys')
      .delete()
      .eq('id', input.id)
      .eq('user_id', uid)
    if (error) throw new Error(error.message)
    return { ok: true }
  })

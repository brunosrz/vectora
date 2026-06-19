import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

Deno.serve(async (req) => {
  if (req.method !== 'POST') {
    return new Response(JSON.stringify({ error: 'Method not allowed' }), {
      status: 405,
    })
  }

  const authHeader = req.headers.get('Authorization')
  if (!authHeader) {
    return new Response(JSON.stringify({ error: 'Unauthorized' }), {
      status: 401,
    })
  }

  const supabaseUrl = Deno.env.get('SUPABASE_URL')!
  const serviceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!

  // Verify calling user
  const anonClient = createClient(
    supabaseUrl,
    Deno.env.get('SUPABASE_ANON_KEY')!,
    {
      global: { headers: { Authorization: authHeader } },
    },
  )
  const {
    data: { user },
    error: authErr,
  } = await anonClient.auth.getUser()
  if (authErr || !user) {
    return new Response(JSON.stringify({ error: 'Unauthorized' }), {
      status: 401,
    })
  }

  const body = await req.json()
  const uid: string = body.user_id ?? user.id
  if (uid !== user.id) {
    return new Response(JSON.stringify({ error: 'Forbidden' }), {
      status: 403,
    })
  }

  const admin = createClient(supabaseUrl, serviceKey)

  // Generate new token
  const rawBytes = crypto.getRandomValues(new Uint8Array(32))
  const newRaw = Array.from(rawBytes)
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('')

  const hashBytes = await crypto.subtle.digest(
    'SHA-256',
    new TextEncoder().encode(newRaw),
  )
  const newHash = Array.from(new Uint8Array(hashBytes))
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('')

  // Compare-and-swap: verify current state before updating
  const { data: current } = await admin
    .from('tokens')
    .select('token_hash')
    .eq('user_id', uid)
    .single()

  if (!current) {
    return new Response(JSON.stringify({ error: 'token_not_found' }), {
      status: 404,
    })
  }

  const { error: updateErr } = await admin
    .from('tokens')
    .update({ token: newRaw, token_hash: newHash })
    .eq('user_id', uid)

  if (updateErr) {
    return new Response(JSON.stringify({ error: updateErr.message }), {
      status: 500,
    })
  }

  return new Response(JSON.stringify({ token: newRaw }), {
    headers: { 'Content-Type': 'application/json' },
  })
})

import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

/**
 * agent-login — login programático do Vectora Agent self-hosted.
 *
 * POST { email, password } →
 *   200 { token, tier, status }  — token pronto para usar como VECTORA_TOKEN
 *   401 { error: "invalid_credentials" }
 *   404 { error: "token_not_found" }
 *
 * Semântica do token (show-once): se o raw ainda existe no banco (nunca foi
 * revelado), ele é entregue e anulado — mesmo fluxo do reveal no dashboard.
 * Se já foi revelado, rotaciona (novo raw + hash), igual ao rotate-token.
 */
Deno.serve(async (req) => {
  if (req.method !== 'POST') {
    return new Response(JSON.stringify({ error: 'Method not allowed' }), {
      status: 405,
    })
  }

  const body = await req.json().catch(() => ({}))
  const email: string | undefined = body.email
  const password: string | undefined = body.password
  if (!email || !password) {
    return new Response(
      JSON.stringify({ error: 'email_and_password_required' }),
      { status: 400 },
    )
  }

  const supabaseUrl = Deno.env.get('SUPABASE_URL')!

  // Autentica com as credenciais do usuário (anon client, sem cookie).
  const anonClient = createClient(
    supabaseUrl,
    Deno.env.get('SUPABASE_ANON_KEY')!,
  )
  const { data: signIn, error: signInErr } =
    await anonClient.auth.signInWithPassword({ email, password })
  if (signInErr || !signIn.user) {
    return new Response(JSON.stringify({ error: 'invalid_credentials' }), {
      status: 401,
    })
  }
  const uid = signIn.user.id

  const admin = createClient(
    supabaseUrl,
    Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!,
  )

  const { data: tokenRow } = await admin
    .from('tokens')
    .select('token, token_hash')
    .eq('user_id', uid)
    .single()

  if (!tokenRow) {
    return new Response(JSON.stringify({ error: 'token_not_found' }), {
      status: 404,
    })
  }

  let raw: string
  if (tokenRow.token) {
    // Nunca revelado — entrega o raw existente e anula (show-once).
    raw = tokenRow.token
    await admin.from('tokens').update({ token: null }).eq('user_id', uid)
  } else {
    // Já revelado — rotaciona: novo raw + hash (invalida o token antigo).
    const rawBytes = crypto.getRandomValues(new Uint8Array(32))
    raw = Array.from(rawBytes)
      .map((b) => b.toString(16).padStart(2, '0'))
      .join('')
    const hashBytes = await crypto.subtle.digest(
      'SHA-256',
      new TextEncoder().encode(raw),
    )
    const newHash = Array.from(new Uint8Array(hashBytes))
      .map((b) => b.toString(16).padStart(2, '0'))
      .join('')
    const { error: updateErr } = await admin
      .from('tokens')
      .update({ token: null, token_hash: newHash })
      .eq('user_id', uid)
    if (updateErr) {
      return new Response(JSON.stringify({ error: updateErr.message }), {
        status: 500,
      })
    }
  }

  const { data: sub } = await admin
    .from('subscriptions')
    .select('tier, status')
    .eq('user_id', uid)
    .single()

  return new Response(
    JSON.stringify({
      token: raw,
      tier: sub?.tier ?? null,
      status: sub?.status ?? null,
    }),
    { headers: { 'Content-Type': 'application/json' } },
  )
})

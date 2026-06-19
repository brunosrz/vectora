import { createSupabaseAdminClient } from './supabase/admin'
import { resend, FROM_EMAIL } from './email/resend'

export interface WaitlistEntry {
  email: string
  country?: 'BR' | 'INTL'
  source?: string
}

export async function addToWaitlist(entry: WaitlistEntry) {
  const supabase = createSupabaseAdminClient()

  const { error } = await (supabase.from('waitlist') as any).upsert(
    {
      email: entry.email,
      country: entry.country ?? null,
      source: entry.source ?? null,
    },
    { onConflict: 'email', ignoreDuplicates: true },
  )

  if (error) throw error

  await resend.emails.send({
    from: FROM_EMAIL,
    to: entry.email,
    subject: 'Você está na lista — Vectora',
    html: `
      <p>Olá!</p>
      <p>Você entrou na lista de espera do Vectora. Avisaremos quando o acesso estiver disponível.</p>
      <p>Enquanto isso, acesse <a href="https://docs.vectora.company">a documentação</a> para saber mais.</p>
      <p>— Bruno, Vectora</p>
    `,
  })
}

import { Resend } from 'resend'

// Init preguiçoso: instanciar o Resend no import quebra QUALQUER server fn que
// importe este módulo quando RESEND_API_KEY não está no ambiente (dev sem email
// configurado). O proxy adia a construção até o primeiro uso real e erra com
// mensagem tipada — o import nunca lança.
let client: Resend | null = null

function getClient(): Resend {
  if (client) return client
  const apiKey = process.env.RESEND_API_KEY
  if (!apiKey) {
    throw new Error(
      'RESEND_API_KEY não configurado — envio de email indisponível.',
    )
  }
  client = new Resend(apiKey)
  return client
}

export const resend = new Proxy({} as Resend, {
  get(_target, prop) {
    return Reflect.get(getClient(), prop)
  },
})

export const FROM_EMAIL = 'noreply@vectora.company'
export const SUPPORT_EMAIL = 'support@vectora.company'
export const BILLING_EMAIL = 'billing@vectora.company'

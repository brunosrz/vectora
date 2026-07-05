/**
 * Envio de email via Resend — chamado direto por fetch (sem o SDK `resend`,
 * pra não adicionar dependência: services segue o mesmo padrão zero-deps de
 * relay/updates, só hono+yaml). Portado de company/src/lib/email/resend.ts +
 * os HTML inline que viviam nas edge functions (webhooks/index.ts).
 */

// Nome de exibição no header "From" — sem isso o Gmail/Outlook mostram só o
// endereço cru na caixa de entrada, sem nome nem identidade visual (o
// avatar da mensagem em si depende de BIMI, que exige registro de marca
// verificado junto ao Google — fora de escopo por ora, o nome já resolve a
// parte que dá pra controlar via header).
export const FROM_EMAIL = "Vectora <noreply@vectora.company>";
export const SUPPORT_EMAIL = "support@vectora.company";

export async function sendEmail(
  apiKey: string,
  params: { to: string; subject: string; html: string; from?: string },
): Promise<void> {
  // Único chamador é o consumer da fila `vectora-email` (queue-consumer.ts)
  // — nenhum handler HTTP chama isso direto (todos enfileiram via
  // enqueueEmail). Por isso lança em erro em vez de só logar: quem decide
  // retry/dead-letter agora é a fila, não esta função.
  const res = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      from: params.from ?? FROM_EMAIL,
      to: params.to,
      subject: params.subject,
      html: params.html,
    }),
  });
  if (!res.ok) {
    const body = await res.text();
    console.error("sendEmail failed", res.status, body);
    throw new Error(`sendEmail failed: ${res.status} ${body}`);
  }
}

function shell(bodyHtml: string): string {
  return `<div style="background:#0a0e1a;font-family:monospace;padding:32px 24px;max-width:560px;margin:0 auto">
    <h1 style="color:#fff;font-size:22px;font-weight:700">Vectora</h1>
    ${bodyHtml}
    <hr style="border-color:#1e293b;margin:24px 0"><p style="color:#475569;font-size:12px">Vectora</p>
  </div>`;
}

// #2563eb é o azul de marca (mesmo accent do produto e do site) — os
// CTAs de email usavam um verde (#4ade80) sem relação com a identidade
// visual do resto do Vectora.
const BRAND_BLUE = "#2563eb";

export function verifyEmailHtml(name: string, verifyUrl: string): string {
  return shell(`
    <p style="color:#94a3b8;font-size:14px">Olá, ${name}! Confirme seu email pra ativar sua conta Vectora.</p>
    <a href="${verifyUrl}" style="display:inline-block;background:${BRAND_BLUE};color:#fff;padding:12px 24px;border-radius:12px;text-decoration:none;font-size:14px;font-weight:600;margin:16px 0">Confirmar email →</a>
  `);
}

export function magicLinkHtml(loginUrl: string): string {
  return shell(`
    <p style="color:#94a3b8;font-size:14px">Clique no link abaixo para entrar no Vectora. Expira em 15 minutos.</p>
    <a href="${loginUrl}" style="display:inline-block;background:${BRAND_BLUE};color:#fff;padding:12px 24px;border-radius:12px;text-decoration:none;font-size:14px;font-weight:600;margin:16px 0">Entrar →</a>
  `);
}

export function invoicePaidHtml(
  name: string,
  amount: string,
  plan: string,
  periodEnd: string,
): string {
  return shell(`
    <p style="color:#4ade80;font-size:14px;font-weight:600">✓ Pagamento confirmado</p>
    <p style="color:#94a3b8;font-size:14px">Olá, ${name}! Recebemos seu pagamento de <strong>${amount}</strong> para o plano <strong>${plan}</strong>. Acesso ativo até ${periodEnd}.</p>
  `);
}

export function invoiceFailedHtml(name: string, amount: string): string {
  return shell(`
    <p style="color:#f87171;font-size:14px;font-weight:600">⚠ Falha no pagamento</p>
    <p style="color:#94a3b8;font-size:14px">Olá, ${name}! Não conseguimos processar o pagamento de <strong>${amount}</strong>. Atualize seu método de pagamento para evitar a suspensão do acesso.</p>
    <a href="https://vectora.company/dashboard/billing" style="display:inline-block;background:#f87171;color:#fff;padding:12px 24px;border-radius:12px;text-decoration:none;font-size:14px;font-weight:600;margin:16px 0">Atualizar pagamento →</a>
  `);
}

export function waitlistJoinedHtml(): string {
  return shell(`
    <p style="color:#94a3b8;font-size:14px">Você entrou na lista de espera do Vectora. Avisaremos quando o acesso estiver disponível.</p>
    <p style="color:#94a3b8;font-size:14px">Enquanto isso, acesse <a href="https://docs.vectora.company" style="color:#4ade80">a documentação</a> para saber mais.</p>
  `);
}

export function giftReceivedHtml(
  granterName: string,
  durationLabel: string,
  ctaUrl: string,
): string {
  return shell(`
    <p style="color:#4ade80;font-size:14px;font-weight:600">🎁 Você recebeu um presente</p>
    <p style="color:#94a3b8;font-size:14px">Você recebeu o Vectora Pro de presente de <strong>${granterName}</strong>! Duração: <strong>${durationLabel}</strong>.</p>
    <a href="${ctaUrl}" style="display:inline-block;background:${BRAND_BLUE};color:#fff;padding:12px 24px;border-radius:12px;text-decoration:none;font-size:14px;font-weight:600;margin:16px 0">Acessar Vectora Pro →</a>
  `);
}

export function accountDeletedHtml(name: string, deletionDate: string): string {
  return shell(`
    <p style="color:#f87171;font-size:14px;font-weight:600">Conta agendada para exclusão</p>
    <p style="color:#94a3b8;font-size:14px">Olá, ${name}. Sua conta e todos os dados serão apagados permanentemente em ${deletionDate}. Se mudar de ideia, é só entrar de novo antes dessa data.</p>
  `);
}

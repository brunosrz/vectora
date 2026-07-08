import { createFileRoute } from "@tanstack/react-router";
import LegalPage from "#/components/shared/LegalPage";

export const Route = createFileRoute("/terms")({
  head: () => ({
    meta: [
      { title: "Termos de Uso — Vectora" },
      {
        property: "og:image",
        content: `/api/og?title=${encodeURIComponent("Termos de Uso")}&desc=${encodeURIComponent("Licença de uso, planos, cancelamento e limitações do Vectora.")}`,
      },
    ],
  }),
  component: TermsPage,
});

function TermsPage() {
  return (
    <LegalPage title="Termos de Uso" lastUpdated="2026-07-08">
      <h2>1. Aceitação</h2>
      <p>
        Ao criar uma conta ou usar o Vectora, você concorda com estes Termos de
        Uso. Se não concordar, não use o serviço.
      </p>

      <h2>2. Licença</h2>
      <p>
        A Vectora concede uma licença não-exclusiva, intransferível e revogável
        para usar o software conforme o plano contratado. Redistribuição ou
        sublicenciamento são proibidos.
      </p>

      <h2>3. Responsabilidades do cliente</h2>
      <ul>
        <li>Manter a segurança do servidor e das credenciais de acesso</li>
        <li>
          Não usar o Vectora para atividades ilegais ou que violem direitos de
          terceiros
        </li>
        <li>Respeitar os limites de uso da API conforme o plano</li>
      </ul>

      <h2>4. Pagamentos e cancelamento</h2>
      <p>
        O plano Free é gratuito e permanente, sem necessidade de cartão de
        crédito. Recursos do plano Pro (chat web multi-usuário, storage
        escalável, webhooks, API REST com limite maior) exigem assinatura paga.
        O cancelamento pode ser feito a qualquer momento pelo painel — a conta
        volta ao plano Free, sem perda de dados locais.
      </p>

      <h2>5. Limitação de responsabilidade</h2>
      <p>
        O Vectora é fornecido "como está". Não nos responsabilizamos por perdas
        de dados, interrupções de serviço ou danos indiretos decorrentes do uso.
      </p>

      <h2 id="acordo-de-nivel-de-servico-sla">
        6. Acordo de nível de serviço (SLA)
      </h2>
      <p>
        <strong>Suporte</strong> — os tempos de resposta variam por plano: Free
        recebe email em até 48 horas úteis; Pro recebe email prioritário em até
        24 horas úteis.
      </p>
      <p>
        <strong>Disponibilidade da plataforma de licença</strong> — a Vectora
        garante 99,5% de uptime mensal para os serviços de autenticação, licença
        e cobrança. O software self-hosted roda na infra do cliente;
        disponibilidade depende do ambiente do cliente.
      </p>
      <p>
        <strong>Exclusões</strong> — o SLA não cobre indisponibilidades causadas
        por manutenções programadas (comunicadas com 48h de antecedência),
        eventos de força maior ou falhas na infra do cliente.
      </p>
      <p>
        <strong>Créditos</strong> — em caso de violação do SLA, o cliente pode
        solicitar crédito proporcional ao período de indisponibilidade. Créditos
        são aplicados na próxima fatura.
      </p>

      <h2>7. Contato</h2>
      <p>
        <a href="mailto:legal@vectora.company">legal@vectora.company</a>
      </p>
    </LegalPage>
  );
}

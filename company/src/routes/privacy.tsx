import { createFileRoute } from "@tanstack/react-router";
import LegalPage from "#/components/shared/LegalPage";

export const Route = createFileRoute("/privacy")({
  head: () => ({
    meta: [
      { title: "Política de Privacidade — Vectora" },
      {
        property: "og:image",
        content: `/api/og?title=${encodeURIComponent("Política de Privacidade")}&desc=${encodeURIComponent("Como o Vectora coleta, usa e protege seus dados. LGPD e GDPR compliant.")}`,
      },
    ],
  }),
  component: PrivacyPage,
});

function PrivacyPage() {
  return (
    <LegalPage title="Política de Privacidade" lastUpdated="2025-01-01">
      <h2>1. Coleta de dados</h2>
      <p>
        O Vectora é uma plataforma self-hosted. Todos os dados — conversas,
        documentos, código e histórico — ficam exclusivamente no servidor do
        cliente. A Vectora não coleta, processa ou armazena conteúdo do
        workspace.
      </p>
      <p>
        Para a licença e cobrança, coletamos: nome, email, país e dados de
        pagamento (processados por Stripe ou Asaas, nunca armazenados
        diretamente pela Vectora).
      </p>

      <h2>2. Uso dos dados</h2>
      <p>Usamos os dados para:</p>
      <ul>
        <li>Autenticação e gerenciamento de licença</li>
        <li>Comunicações sobre a conta (faturas, alertas de trial, suporte)</li>
        <li>Análise de uso agregada e anônima via Plausible (self-hosted)</li>
      </ul>

      <h2>3. Compartilhamento</h2>
      <p>
        Não vendemos dados. Compartilhamos apenas com provedores de pagamento
        (Stripe, Asaas) e email transacional (Resend) conforme necessário para
        operar o serviço.
      </p>

      <h2>4. LGPD / GDPR</h2>
      <p>
        Você pode exportar ou solicitar a exclusão de seus dados a qualquer
        momento pelo painel em /dashboard/account. A exclusão é processada em
        até 30 dias.
      </p>

      <h2>5. Contato</h2>
      <p>
        <a href="mailto:privacy@vectora.company">privacy@vectora.company</a>
      </p>
    </LegalPage>
  );
}

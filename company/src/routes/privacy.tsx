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
    <LegalPage title="Política de Privacidade" lastUpdated="2026-07-08">
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
        <li>
          Comunicações sobre a conta (faturas, status de pagamento, suporte)
        </li>
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

      <h2 id="cookies-e-analytics">5. Cookies e analytics</h2>
      <p>O site vectora.company utiliza:</p>
      <ul>
        <li>
          <strong>vsession</strong> — Autenticação Vectora. HTTPOnly, Secure.
        </li>
        <li>
          <strong>cf_clearance</strong> — Verificação Cloudflare Turnstile
          (temporário).
        </li>
        <li>
          <strong>Plausible Analytics</strong> — análise de uso agregada e
          anônima, self-hosted, sem cookies.
        </li>
        <li>
          <strong>Google Analytics 4</strong> — complementa o Plausible com
          dados de funil e Search Console. Usa Google Consent Mode v2:
          desabilitado por padrão (<code>analytics_storage: denied</code>), só é
          ativado se você aceitar no banner de cookies exibido na primeira
          visita. Você pode revogar o consentimento a qualquer momento limpando
          os cookies do navegador.
        </li>
      </ul>
      <p>
        Não utilizamos cookies de rastreamento publicitário — nenhum dos
        mecanismos acima é usado para anúncios ou perfis de terceiros.
      </p>

      <h2 id="processamento-de-dados-dpa">6. Processamento de dados (DPA)</h2>
      <p>
        Esta seção complementa a Política de Privacidade e aplica-se ao
        processamento de dados pessoais realizado pela Vectora em nome do
        cliente, conforme exigido pela LGPD (Lei 13.709/2018) e GDPR
        (Regulamento UE 2016/679).
      </p>
      <p>
        <strong>Papéis</strong> — o cliente é o Controlador (determina as
        finalidades do processamento); a Vectora é o Operador (processa dados
        conforme as instruções do controlador).
      </p>
      <p>
        <strong>Natureza do processamento</strong> — como o Vectora é
        self-hosted, os dados do workspace (documentos, conversas, código) ficam
        exclusivamente na infra do cliente. A Vectora processa apenas dados de
        conta necessários para autenticação e cobrança.
      </p>
      <p>
        <strong>Subprocessadores</strong>
      </p>
      <ul>
        <li>
          <strong>Cloudflare</strong> — autenticação e banco de dados de licença
          (dados de conta), infraestrutura própria da Vectora
        </li>
        <li>
          <strong>Stripe / Asaas</strong> — processamento de pagamentos
        </li>
        <li>
          <strong>Resend</strong> — email transacional
        </li>
      </ul>
      <p>
        <strong>Direitos dos titulares</strong> — solicitações de acesso,
        correção, portabilidade e exclusão podem ser feitas em
        /dashboard/account ou via{" "}
        <a href="mailto:privacy@vectora.company">privacy@vectora.company</a>.
      </p>

      <h2>7. Contato</h2>
      <p>
        <a href="mailto:privacy@vectora.company">privacy@vectora.company</a>
      </p>
    </LegalPage>
  );
}

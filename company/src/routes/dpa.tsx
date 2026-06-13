import { createFileRoute } from "@tanstack/react-router";
import LegalPage from "#/components/shared/LegalPage";

export const Route = createFileRoute("/dpa")({
  head: () => ({
    meta: [
      { title: "DPA — Vectora" },
      {
        property: "og:image",
        content: `/api/og?title=${encodeURIComponent("Data Processing Agreement")}&desc=${encodeURIComponent("Template EU DPA padrão ICC. LGPD e GDPR para Enterprise.")}`,
      },
    ],
  }),
  component: DpaPage,
});

function DpaPage() {
  return (
    <LegalPage
      title="Acordo de Processamento de Dados (DPA)"
      lastUpdated="2025-01-01"
    >
      <h2>1. Escopo</h2>
      <p>
        Este DPA complementa os Termos de Uso e aplica-se ao processamento de
        dados pessoais realizado pela Vectora em nome do cliente, conforme
        exigido pela LGPD (Lei 13.709/2018) e GDPR (Regulamento UE 2016/679).
      </p>

      <h2>2. Papéis</h2>
      <ul>
        <li>
          <strong>Controlador</strong> — O cliente, que determina as finalidades
          do processamento.
        </li>
        <li>
          <strong>Operador</strong> — A Vectora, que processa dados conforme as
          instruções do controlador.
        </li>
      </ul>

      <h2>3. Natureza do processamento</h2>
      <p>
        Como o Vectora é self-hosted, os dados do workspace (documentos,
        conversas, código) ficam exclusivamente na infra do cliente. A Vectora
        processa apenas dados de conta necessários para autenticação e cobrança.
      </p>

      <h2>4. Subprocessadores</h2>
      <ul>
        <li>
          <strong>Supabase</strong> — Autenticação e banco de dados de licença
          (dados de conta)
        </li>
        <li>
          <strong>Stripe / Asaas</strong> — Processamento de pagamentos
        </li>
        <li>
          <strong>Resend</strong> — Email transacional
        </li>
      </ul>

      <h2>5. Direitos dos titulares</h2>
      <p>
        Solicitações de acesso, correção, portabilidade e exclusão podem ser
        feitas em /dashboard/account ou via{" "}
        <a href="mailto:privacy@vectora.company">privacy@vectora.company</a>.
      </p>
    </LegalPage>
  );
}

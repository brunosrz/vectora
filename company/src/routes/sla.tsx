import { createFileRoute } from "@tanstack/react-router";
import LegalPage from "#/components/shared/LegalPage";

export const Route = createFileRoute("/sla")({
  head: () => ({
    meta: [
      { title: "SLA — Vectora" },
      {
        property: "og:image",
        content: `/api/og?title=${encodeURIComponent("Acordo de Nível de Serviço")}&desc=${encodeURIComponent("Uptime ≥ 99.5% para validate-license. Latência p95 < 500ms.")}`,
      },
    ],
  }),
  component: SlaPage,
});

function SlaPage() {
  return (
    <LegalPage
      title="Acordo de Nível de Serviço (SLA)"
      lastUpdated="2025-01-01"
    >
      <h2>Suporte</h2>
      <p>Os tempos de resposta de suporte variam por plano:</p>
      <ul>
        <li>
          <strong>Trial</strong> — Comunidade (GitHub Issues, sem SLA)
        </li>
        <li>
          <strong>Plus</strong> — Email em até 48 horas úteis
        </li>
        <li>
          <strong>Pro</strong> — Email prioritário em até 24 horas úteis
        </li>
      </ul>

      <h2>Disponibilidade da plataforma de licença</h2>
      <p>
        A Vectora garante 99,5% de uptime mensal para os serviços de
        autenticação, licença e cobrança. O software self-hosted roda na infra
        do cliente; disponibilidade depende do ambiente do cliente.
      </p>

      <h2>Exclusões</h2>
      <p>
        O SLA não cobre indisponibilidades causadas por manutenções programadas
        (comunicadas com 48h de antecedência), eventos de força maior ou falhas
        na infra do cliente.
      </p>

      <h2>Créditos</h2>
      <p>
        Em caso de violação do SLA, o cliente pode solicitar crédito
        proporcional ao período de indisponibilidade. Créditos são aplicados na
        próxima fatura.
      </p>
    </LegalPage>
  );
}

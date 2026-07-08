import { createFileRoute, redirect } from "@tanstack/react-router";

// SLA consolidado em /terms (seção "Acordo de nível de serviço (SLA)") —
// rota mantida só como redirect pra não quebrar links/bookmarks antigos.
export const Route = createFileRoute("/sla")({
  beforeLoad: () => {
    throw redirect({ to: "/terms", hash: "acordo-de-nivel-de-servico-sla" });
  },
});

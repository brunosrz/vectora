import { createFileRoute, redirect } from "@tanstack/react-router";

// DPA consolidado em /privacy (seção "Processamento de dados (DPA)") —
// rota mantida só como redirect pra não quebrar links/bookmarks antigos.
export const Route = createFileRoute("/dpa")({
  beforeLoad: () => {
    throw redirect({ to: "/privacy", hash: "processamento-de-dados-dpa" });
  },
});

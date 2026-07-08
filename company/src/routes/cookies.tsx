import { createFileRoute, redirect } from "@tanstack/react-router";

// Política de Cookies consolidada em /privacy (seção "Cookies e analytics") —
// rota mantida só como redirect pra não quebrar links/bookmarks antigos.
export const Route = createFileRoute("/cookies")({
  beforeLoad: () => {
    throw redirect({ to: "/privacy", hash: "cookies-e-analytics" });
  },
});

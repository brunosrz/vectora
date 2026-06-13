import { createFileRoute } from "@tanstack/react-router";
import LegalPage from "#/components/shared/LegalPage";

export const Route = createFileRoute("/cookies")({
  head: () => ({
    meta: [
      { title: "Política de Cookies — Vectora" },
      {
        property: "og:image",
        content: `/api/og?title=${encodeURIComponent("Política de Cookies")}&desc=${encodeURIComponent("Apenas cookies essenciais de autenticação. Sem rastreamento.")}`,
      },
    ],
  }),
  component: CookiesPage,
});

function CookiesPage() {
  return (
    <LegalPage title="Política de Cookies" lastUpdated="2025-01-01">
      <h2>Cookies utilizados</h2>
      <p>O Vectora utiliza apenas cookies estritamente necessários:</p>
      <ul>
        <li>
          <strong>sb-access-token / sb-refresh-token</strong> — Autenticação
          Supabase. HTTPOnly, Secure.
        </li>
        <li>
          <strong>cf_clearance</strong> — Verificação Cloudflare Turnstile
          (temporário).
        </li>
      </ul>
      <p>
        Não utilizamos cookies de rastreamento publicitário. Nossa análise de
        uso é feita via Plausible Analytics, que opera sem cookies.
      </p>

      <h2>Gerenciamento</h2>
      <p>
        Você pode limpar os cookies pelo seu navegador a qualquer momento. Isso
        encerrará sua sessão.
      </p>
    </LegalPage>
  );
}

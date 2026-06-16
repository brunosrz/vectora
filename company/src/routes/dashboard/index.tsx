import { createFileRoute } from "@tanstack/react-router";
import { z } from "zod";
import { m } from "#/paraglide/messages";
import { getTokenStatus } from "#/server/fns/token";
import TokenReveal from "#/components/dashboard/TokenReveal";
import DashboardHeading from "#/components/dashboard/DashboardHeading";

const SearchSchema = z.object({ welcome: z.boolean().optional() });

export const Route = createFileRoute("/dashboard/")({
  validateSearch: SearchSchema,
  loader: async () => {
    const status = await getTokenStatus();
    return { revealed: status.revealed };
  },
  component: DashboardIndexPage,
});

function DashboardIndexPage() {
  const { revealed } = Route.useLoaderData();
  const { welcome } = Route.useSearch();

  return (
    <div>
      <DashboardHeading title={m.nav_token()} />
      <TokenReveal initialRevealed={revealed} welcome={welcome} />
    </div>
  );
}

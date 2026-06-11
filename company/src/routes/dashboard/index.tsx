import { createFileRoute } from "@tanstack/react-router";
import { z } from "zod";
import { getTokenStatus } from "#/server/fns/token";
import TokenReveal from "#/components/dashboard/TokenReveal";

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
      <h1 className="mb-6 text-2xl font-semibold text-foreground">Token</h1>
      <TokenReveal initialRevealed={revealed} welcome={welcome} />
    </div>
  );
}

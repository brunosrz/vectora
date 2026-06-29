import { createFileRoute, redirect } from "@tanstack/react-router";
import { getSession } from "#/server/fns/auth";
import { m } from "#/paraglide/messages";

export const Route = createFileRoute("/dashboard")({
  beforeLoad: async () => {
    const user = await getSession();
    if (!user) throw redirect({ to: "/login" });
  },
  head: () => ({ meta: [{ title: m.page_dashboard_title() }] }),
  component: DashboardPage,
});

function DashboardPage() {
  return (
    <div className="flex min-h-[calc(100vh-4rem)] flex-col items-center justify-center gap-4 px-4 text-center">
      <h1 className="text-2xl font-bold text-foreground">
        {m.dashboard_heading()}
      </h1>
      <p className="text-muted-foreground">{m.dashboard_desc()}</p>
    </div>
  );
}

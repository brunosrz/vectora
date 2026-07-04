import { createFileRoute, Outlet, redirect } from "@tanstack/react-router";
import { getSession } from "#/server/fns/auth";
import Sidebar from "#/components/dashboard/Sidebar";

export const Route = createFileRoute("/dashboard")({
  beforeLoad: async ({ location }) => {
    const user = await getSession();
    if (!user) {
      throw redirect({ to: "/login", search: { redirect: location.pathname } });
    }
    return { user };
  },
  head: () => ({
    meta: [{ name: "robots", content: "noindex, nofollow" }],
  }),
  component: DashboardLayout,
});

function DashboardLayout() {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 overflow-y-auto bg-background p-6 pb-24 lg:pb-6">
        <div className="mx-auto w-full max-w-[1024px]">
          <Outlet />
        </div>
      </main>
    </div>
  );
}

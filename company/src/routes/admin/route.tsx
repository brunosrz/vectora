import { createFileRoute, Outlet, redirect } from "@tanstack/react-router";
import { getSession } from "#/server/fns/auth";
import Sidebar from "#/components/dashboard/Sidebar";
import AdminTabs from "#/components/admin/AdminTabs";

export const Route = createFileRoute("/admin")({
  beforeLoad: async ({ location }) => {
    const user = await getSession();
    if (!user) {
      throw redirect({ to: "/login", search: { redirect: location.pathname } });
    }
    // Não revela a existência da rota pra quem não é admin — cai no
    // dashboard normal, não num /403 ou /login que denunciaria a rota.
    if (user.role !== "admin") {
      throw redirect({ to: "/dashboard" });
    }
    return { user };
  },
  head: () => ({
    meta: [{ name: "robots", content: "noindex, nofollow" }],
  }),
  component: AdminLayout,
});

function AdminLayout() {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 overflow-y-auto bg-background p-6 pb-24 lg:pb-6">
        <div className="mx-auto w-full max-w-[1024px]">
          <AdminTabs />
          <Outlet />
        </div>
      </main>
    </div>
  );
}

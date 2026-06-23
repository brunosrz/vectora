import { createFileRoute, Outlet, redirect } from "@tanstack/react-router";
import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { getSession } from "#/server/fns/auth";
import { getSupabaseBrowserClient } from "#/lib/supabase/client";
import { useAuthStore } from "#/store/auth";
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
  const qc = useQueryClient();
  const uid = useAuthStore((s) => s.session?.id);

  useEffect(() => {
    if (!uid) return;
    const supabase = getSupabaseBrowserClient();
    if (!supabase) return;

    const channel = supabase
      .channel("license_status")
      .on(
        "postgres_changes",
        {
          event: "*",
          schema: "public",
          table: "subscriptions",
          filter: `user_id=eq.${uid}`,
        },
        () => {
          qc.invalidateQueries({ queryKey: ["subscription"] });
        },
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [uid, qc]);

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

import { Link, useRouterState } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { m } from "#/paraglide/messages";
import { listIssuesAdmin } from "#/server/fns/admin";

const TABS = [
  { to: "/admin" as const, exact: true, label: m.admin_tab_users },
  {
    to: "/admin/coupons" as const,
    exact: false,
    label: m.admin_tab_coupons,
  },
  {
    to: "/admin/gifts" as const,
    exact: false,
    label: m.admin_tab_gifts,
  },
  {
    to: "/admin/issues" as const,
    exact: false,
    label: m.admin_tab_issues,
  },
] as const;

export default function AdminTabs() {
  const { location } = useRouterState();
  const pathname = location.pathname;
  // Badge de contagem de issues abertas = a notificação in-app pedida —
  // sem tabela/sistema de notificação novo, só reaproveita a mesma listagem
  // que a aba Issues já usa.
  const { data } = useQuery({
    queryKey: ["admin-issues"],
    queryFn: () => listIssuesAdmin({ data: {} }),
  });
  const openCount = data?.issues.filter((i) => i.status === "open").length ?? 0;

  return (
    <nav className="mb-6 flex gap-1 border-b border-border">
      {TABS.map((tab) => {
        const active = tab.exact
          ? pathname === tab.to
          : pathname.startsWith(tab.to);
        return (
          <Link
            key={tab.to}
            to={tab.to}
            className={`flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
              active
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            {tab.label()}
            {tab.to === "/admin/issues" && openCount > 0 && (
              <span className="rounded-full bg-primary px-1.5 py-0.5 text-[10px] font-semibold text-primary-foreground">
                {openCount}
              </span>
            )}
          </Link>
        );
      })}
    </nav>
  );
}

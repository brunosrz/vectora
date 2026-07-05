import { Link, useRouterState } from "@tanstack/react-router";
import { m } from "#/paraglide/messages";

const TABS = [
  { to: "/admin" as const, exact: true, labelKey: "admin_tab_users" as const },
  {
    to: "/admin/coupons" as const,
    exact: false,
    labelKey: "admin_tab_coupons" as const,
  },
  {
    to: "/admin/gifts" as const,
    exact: false,
    labelKey: "admin_tab_gifts" as const,
  },
] as const;

export default function AdminTabs() {
  const { location } = useRouterState();
  const pathname = location.pathname;

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
            className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
              active
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            {m[tab.labelKey]()}
          </Link>
        );
      })}
    </nav>
  );
}

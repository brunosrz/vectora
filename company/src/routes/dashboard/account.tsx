import { createFileRoute } from "@tanstack/react-router";
import { m } from "#/paraglide/messages";
import AccountSection from "#/components/dashboard/AccountSection";
import DashboardHeading from "#/components/dashboard/DashboardHeading";

export const Route = createFileRoute("/dashboard/account")({
  component: AccountPage,
});

function AccountPage() {
  const { user } = Route.useRouteContext();
  return (
    <div>
      <DashboardHeading title={m.nav_account()} />
      <AccountSection user={user} />
    </div>
  );
}

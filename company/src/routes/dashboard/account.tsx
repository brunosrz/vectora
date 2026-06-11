import { createFileRoute } from "@tanstack/react-router";
import { m } from "#/paraglide/messages";
import AccountSection from "#/components/dashboard/AccountSection";

export const Route = createFileRoute("/dashboard/account")({
  component: AccountPage,
});

function AccountPage() {
  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold text-white">
        {m.nav_account()}
      </h1>
      <AccountSection />
    </div>
  );
}

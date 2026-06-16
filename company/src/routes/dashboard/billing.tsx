import { createFileRoute } from "@tanstack/react-router";
import { m } from "#/paraglide/messages";
import BillingSection from "#/components/dashboard/BillingSection";
import DashboardHeading from "#/components/dashboard/DashboardHeading";

export const Route = createFileRoute("/dashboard/billing")({
  component: BillingPage,
});

function BillingPage() {
  return (
    <div>
      <DashboardHeading title={m.nav_billing()} />
      <BillingSection />
    </div>
  );
}

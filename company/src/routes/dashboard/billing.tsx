import { createFileRoute } from "@tanstack/react-router";
import { m } from "#/paraglide/messages";
import BillingSection from "#/components/dashboard/BillingSection";

export const Route = createFileRoute("/dashboard/billing")({
  component: BillingPage,
});

function BillingPage() {
  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold text-white">
        {m.nav_billing()}
      </h1>
      <BillingSection />
    </div>
  );
}

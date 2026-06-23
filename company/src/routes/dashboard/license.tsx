import { createFileRoute } from "@tanstack/react-router";
import { m } from "#/paraglide/messages";
import {
  LicenseStatus,
  LicenseHistory,
} from "#/components/dashboard/LicenseStatus";
import DashboardHeading from "#/components/dashboard/DashboardHeading";

export const Route = createFileRoute("/dashboard/license")({
  component: LicensePage,
});

function LicensePage() {
  return (
    <div>
      <DashboardHeading title={m.nav_license()} />
      <LicenseStatus />
      <div className="mt-8 max-w-3xl">
        <h2 className="mb-4 text-base font-medium text-foreground">
          {m.license_history_heading()}
        </h2>
        <LicenseHistory />
      </div>
    </div>
  );
}

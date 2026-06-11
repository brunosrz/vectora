import { createFileRoute } from "@tanstack/react-router";
import { m } from "#/paraglide/messages";
import {
  LicenseStatus,
  LicenseHistory,
} from "#/components/dashboard/LicenseStatus";

export const Route = createFileRoute("/dashboard/license")({
  component: LicensePage,
});

function LicensePage() {
  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold text-white">
        {m.nav_license()}
      </h1>
      <LicenseStatus />
      <div className="mt-8 max-w-3xl">
        <h2 className="mb-4 text-base font-medium text-white">
          {m.license_history_heading()}
        </h2>
        <LicenseHistory />
      </div>
    </div>
  );
}

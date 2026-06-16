import { createFileRoute } from "@tanstack/react-router";
import { m } from "#/paraglide/messages";
import ApiKeysList from "#/components/dashboard/ApiKeysList";
import DashboardHeading from "#/components/dashboard/DashboardHeading";

export const Route = createFileRoute("/dashboard/api-keys")({
  component: ApiKeysPage,
});

function ApiKeysPage() {
  return (
    <div>
      <DashboardHeading
        title={m.nav_api_keys()}
        subtitle={m.apikeys_subtitle()}
      />
      <ApiKeysList />
    </div>
  );
}

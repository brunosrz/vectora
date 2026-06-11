import { createFileRoute } from "@tanstack/react-router";
import { m } from "#/paraglide/messages";
import ApiKeysList from "#/components/dashboard/ApiKeysList";

export const Route = createFileRoute("/dashboard/api-keys")({
  component: ApiKeysPage,
});

function ApiKeysPage() {
  return (
    <div>
      <h1 className="mb-2 text-2xl font-semibold text-white">
        {m.nav_api_keys()}
      </h1>
      <p className="mb-6 text-sm text-slate-400">{m.apikeys_subtitle()}</p>
      <ApiKeysList />
    </div>
  );
}

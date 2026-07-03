/**
 * vectora-services — Worker único que substitui `relay/`, `update-server/`
 * e o backend Supabase da company. Dispatch por hostname:
 *
 * - `relay.vectora.chat` e `{token}.vectora.chat` → relay (WebSocket
 *   bidirecional de OAuth/webhooks pro app desktop — protocolo já embutido
 *   no cliente Python, domínio não muda).
 * - `update.vectora.company` → updates (electron-updater + download público).
 * - Qualquer outro host (`services.vectora.company`) → auth/profile/billing/
 *   license/gdpr/api-keys/issues/rag-library/registry.
 */

import { Hono } from "hono";
import relayHandler, {
  RelaySession,
  RELAY_HOST,
  RELAY_BASE_DOMAIN,
} from "./relay";
import updatesApp from "./updates/worker";
import { auth } from "./auth/routes";
import { profile } from "./profile/routes";
import { billing } from "./billing/routes";
import { license } from "./license/routes";
import { oauth } from "./oauth/routes";
import { gdpr, hardDeleteExpiredUsers } from "./gdpr/routes";
import { apiKeys } from "./api-keys/routes";
import { issues } from "./issues/routes";
import { ragLibrary } from "./rag-library/routes";
import { registry } from "./registry/routes";
import type { Env } from "./relay/types";

export { RelaySession };

function isRelayHost(hostname: string): boolean {
  return hostname === RELAY_HOST || hostname.endsWith(`.${RELAY_BASE_DOMAIN}`);
}

const servicesApp = new Hono<{ Bindings: Env }>();
servicesApp.route("/auth", auth);
servicesApp.route("/profile", profile);
servicesApp.route("/billing", billing);
servicesApp.route("/license", license);
servicesApp.route("/oauth", oauth);
servicesApp.route("/gdpr", gdpr);
servicesApp.route("/api-keys", apiKeys);
servicesApp.route("/issues", issues);
servicesApp.route("/rag-library", ragLibrary);
servicesApp.route("/registry", registry);
servicesApp.get("/health", (c) =>
  c.json({ ok: true, server: "vectora-services" }),
);

export default {
  fetch(
    request: Request,
    env: Env,
    ctx: ExecutionContext,
  ): Response | Promise<Response> {
    const { hostname } = new URL(request.url);
    if (isRelayHost(hostname)) {
      return relayHandler.fetch(request, env);
    }
    if (hostname === "update.vectora.company") {
      return updatesApp.fetch(request, env, ctx);
    }
    return servicesApp.fetch(request, env, ctx);
  },

  async scheduled(
    _controller: ScheduledController,
    env: Env,
    ctx: ExecutionContext,
  ): Promise<void> {
    ctx.waitUntil(hardDeleteExpiredUsers(env).then(() => undefined));
  },
} satisfies ExportedHandler<Env>;

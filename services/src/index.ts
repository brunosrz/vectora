/**
 * vectora-services — Worker único que serve `relay/`, `updates/` e o
 * backend da company. Dispatch por hostname:
 *
 * - `relay.vectora.chat` e `{token}.vectora.chat` → relay (WebSocket
 *   bidirecional de OAuth/webhooks pro app desktop — protocolo já embutido
 *   no cliente Python, domínio não muda).
 * - Qualquer outro host → um único Hono app com auth/profile/billing/
 *   license/gdpr/api-keys/issues/rag-library/registry/telemetry e updates
 *   (electron-updater + download público, `src/updates/worker.ts`, mesclado
 *   na raiz via `.route("/", ...)`) — sem domínio dedicado.
 *
 * `queue()` processa as duas filas do Worker (`vectora-email`, `vectora-jobs`
 * — ver src/queue-consumer.ts e wrangler.toml).
 */

import { Hono } from "hono";
import relayHandler, {
  RelaySession,
  RELAY_HOST,
  RELAY_BASE_DOMAIN,
} from "./relay";
import updatesApp from "./updates/worker";
import { auth } from "./auth/routes";
import { admin } from "./admin/routes";
import { profile } from "./profile/routes";
import { billing } from "./billing/routes";
import { license } from "./license/routes";
import { oauth } from "./oauth/routes";
import { gdpr, enqueueExpiredUserDeletions } from "./gdpr/routes";
import { expireGiftSubscriptions } from "./billing/routes";
import { apiKeys } from "./api-keys/routes";
import { issues } from "./issues/routes";
import { ragLibrary } from "./rag-library/routes";
import { registry } from "./registry/routes";
import { telemetry } from "./telemetry/routes";
import { handleQueue } from "./queue-consumer";
import type { Env } from "./relay/types";

export { RelaySession };

function isRelayHost(hostname: string): boolean {
  return hostname === RELAY_HOST || hostname.endsWith(`.${RELAY_BASE_DOMAIN}`);
}

const servicesApp = new Hono<{ Bindings: Env }>();
servicesApp.route("/auth", auth);
servicesApp.route("/admin", admin);
servicesApp.route("/profile", profile);
servicesApp.route("/billing", billing);
servicesApp.route("/license", license);
servicesApp.route("/oauth", oauth);
servicesApp.route("/gdpr", gdpr);
servicesApp.route("/api-keys", apiKeys);
servicesApp.route("/issues", issues);
servicesApp.route("/rag-library", ragLibrary);
servicesApp.route("/registry", registry);
servicesApp.route("/telemetry", telemetry);
// updates/worker.ts mesclado na raiz, sem prefixo: /download/*, /updates/*,
// /telemetry/update-result somam às rotas acima.
servicesApp.route("/", updatesApp);
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
    return servicesApp.fetch(request, env, ctx);
  },

  async scheduled(
    _controller: ScheduledController,
    env: Env,
    ctx: ExecutionContext,
  ): Promise<void> {
    ctx.waitUntil(enqueueExpiredUserDeletions(env).then(() => undefined));
    ctx.waitUntil(expireGiftSubscriptions(env.DB).then(() => undefined));
  },

  async queue(batch: MessageBatch<unknown>, env: Env): Promise<void> {
    await handleQueue(batch, env);
  },
} satisfies ExportedHandler<Env>;

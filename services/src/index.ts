/**
 * vectora-services — Worker único que substitui os antigos `relay/` e
 * `update-server/` (Fase A do plano de unificação). Dispatch por hostname:
 *
 * - `relay.vectora.chat` e `{token}.vectora.chat` → relay (WebSocket
 *   bidirecional de OAuth/webhooks pro app desktop — protocolo já embutido
 *   no cliente Python, domínio não muda).
 * - Qualquer outro host (`update.vectora.company`, futuramente
 *   `services.vectora.company`) → app Hono com as rotas de updates (e, nas
 *   próximas fases, auth/billing/license/gdpr/rag-library/registry).
 */

import relayHandler, {
  RelaySession,
  RELAY_HOST,
  RELAY_BASE_DOMAIN,
} from "./relay";
import updatesApp from "./updates/worker";
import type { Env } from "./relay/types";

export { RelaySession };

function isRelayHost(hostname: string): boolean {
  return hostname === RELAY_HOST || hostname.endsWith(`.${RELAY_BASE_DOMAIN}`);
}

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
    return updatesApp.fetch(request, env, ctx);
  },
} satisfies ExportedHandler<Env>;

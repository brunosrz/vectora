import { timingSafeEqual, generateGatewayToken } from "./auth";
import { GatewaySession } from "./gateway-session";
import type { Env, RegisterRequest, RegisterResponse } from "./types";

export { GatewaySession };

export const GATEWAY_HOST = "gateway.vectora.chat";
export const GATEWAY_BASE_DOMAIN = "vectora.chat";

const gatewayHandler = {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    const host = url.hostname;

    // Subdomínio de sessão: {token}.vectora.chat
    if (host !== GATEWAY_HOST && host.endsWith(`.${GATEWAY_BASE_DOMAIN}`)) {
      const token = host.slice(0, -`.${GATEWAY_BASE_DOMAIN}`.length);
      return routeToSession(request, token, env, url);
    }

    // Endpoints do gateway em gateway.vectora.chat
    if (request.method === "POST" && url.pathname === "/register") {
      return handleRegister(request, env);
    }

    if (url.pathname.startsWith("/ws/")) {
      const token = url.pathname.slice(4);
      if (!token) return new Response("Bad Request", { status: 400 });
      if (request.headers.get("Upgrade") !== "websocket") {
        return new Response("Expected WebSocket upgrade", { status: 426 });
      }
      return routeToSession(request, token, env, url);
    }

    if (url.pathname.startsWith("/health/")) {
      const token = url.pathname.slice(8);
      if (!token) return new Response("Bad Request", { status: 400 });
      return routeToSession(
        new Request(`https://${GATEWAY_HOST}/_health`, { method: "GET" }),
        token,
        env,
        url,
      );
    }

    if (
      request.method === "DELETE" &&
      url.pathname.startsWith("/gateway/session/")
    ) {
      const token = url.pathname.slice("/gateway/session/".length);
      if (!token) return new Response("Bad Request", { status: 400 });
      return routeToSession(
        new Request(`https://${GATEWAY_HOST}/_revoke`, { method: "DELETE" }),
        token,
        env,
        url,
      );
    }

    // OAuth device flow — company armazena, backend consome
    if (request.method === "POST" && url.pathname === "/oauth/token") {
      return handleOAuthStore(request, env);
    }

    if (request.method === "GET" && url.pathname.startsWith("/oauth/token/")) {
      const state = url.pathname.slice("/oauth/token/".length);
      return handleOAuthPoll(state, request, env);
    }

    return new Response("Not Found", { status: 404 });
  },
} satisfies ExportedHandler<Env>;

export default gatewayHandler;

/** Prova que quem chama é um build genuíno do Vectora — secret fixo por
 * produto, embutido no binário Nuitka, igual pra toda instalação (não é
 * por-usuário — nunca foi: o esquema anterior via JWT sempre assinava com
 * `sub: "relay-system"`, uma constante, então trocar pra um secret fixo
 * comparado em texto não perde granularidade nenhuma que já existisse). */
function requireAppSecret(request: Request, env: Env): boolean {
  const auth = request.headers.get("Authorization") ?? "";
  const expected = `Bearer ${env.VECTORA_APP_SECRET}`;
  return timingSafeEqual(auth, expected);
}

async function handleRegister(request: Request, env: Env): Promise<Response> {
  if (!requireAppSecret(request, env)) {
    return new Response("Unauthorized", { status: 401 });
  }

  let body: RegisterRequest;
  try {
    body = (await request.json()) as RegisterRequest;
  } catch {
    return new Response("Bad Request", { status: 400 });
  }

  if (!body.fingerprint) {
    return new Response("Bad Request — fingerprint required", {
      status: 400,
    });
  }

  const token = await generateGatewayToken(
    body.fingerprint,
    env.GATEWAY_HMAC_SECRET,
  );
  const response: RegisterResponse = {
    token,
    subdomain: `${token}.${GATEWAY_BASE_DOMAIN}`,
    websocket_url: `wss://${GATEWAY_HOST}/ws/${token}`,
  };

  return Response.json(response);
}

const OAUTH_TTL_SECONDS = 300; // 5 min

function requireOAuthSecret(request: Request, env: Env): boolean {
  const auth = request.headers.get("Authorization") ?? "";
  return auth === `Bearer ${env.VECTORA_OAUTH_SECRET}`;
}

async function handleOAuthStore(request: Request, env: Env): Promise<Response> {
  if (!requireOAuthSecret(request, env)) {
    return new Response("Unauthorized", { status: 401 });
  }
  let body: { state: string; token: string };
  try {
    body = (await request.json()) as { state: string; token: string };
  } catch {
    return new Response("Bad Request", { status: 400 });
  }
  if (!body.state || !body.token) {
    return new Response("Bad Request — state and token required", {
      status: 400,
    });
  }
  await env.GATEWAY_METRICS.put(`oauth:${body.state}`, body.token, {
    expirationTtl: OAUTH_TTL_SECONDS,
  });
  return Response.json({ ok: true });
}

async function handleOAuthPoll(
  state: string,
  request: Request,
  env: Env,
): Promise<Response> {
  if (!requireOAuthSecret(request, env)) {
    return new Response("Unauthorized", { status: 401 });
  }
  if (!state) return new Response("Bad Request", { status: 400 });
  const token = await env.GATEWAY_METRICS.get(`oauth:${state}`);
  if (!token) return new Response("Pending", { status: 202 });
  await env.GATEWAY_METRICS.delete(`oauth:${state}`);
  return Response.json({ token });
}

function routeToSession(
  request: Request,
  token: string,
  env: Env,
  _url: URL,
): Promise<Response> {
  const maxBytes = parseInt(env.MAX_PAYLOAD_BYTES ?? "5242880", 10);
  const contentLength = parseInt(
    request.headers.get("content-length") ?? "0",
    10,
  );
  if (contentLength > maxBytes) {
    return Promise.resolve(new Response("Payload Too Large", { status: 413 }));
  }
  const id = env.GATEWAY_SESSION.idFromName(token);
  const stub = env.GATEWAY_SESSION.get(id);
  return stub.fetch(request);
}

/** Header só o próprio Worker sabe montar — usado nas chamadas internas
 * pra `GatewaySession` (`/_health`, `/_revoke`, `/_dispatch-job`) pra
 * provar que não vieram de um client externo batendo direto no
 * subdomínio (ver `GatewaySession::isInternalCall`). */
function internalHeaders(env: Env): Record<string, string> {
  return { "X-Vectora-Internal": `Bearer ${env.VECTORA_APP_SECRET}` };
}

/** Consultado por gha-bot/routes.ts (GET /gha-bot/config) pra só oferecer
 * o modo self-hosted quando a instância do usuário está de fato
 * conectada — chamada em-processo (DO stub), sem hop de rede real. */
export async function checkGatewayHealth(
  env: Env,
  token: string,
): Promise<{ connected: boolean }> {
  const res = await routeToSession(
    new Request(`https://${GATEWAY_HOST}/_health`, {
      method: "GET",
      headers: internalHeaders(env),
    }),
    token,
    env,
    new URL(`https://${GATEWAY_HOST}/_health`),
  );
  if (!res.ok) return { connected: false };
  return res.json();
}

/** Despacha um review_job fire-and-forget pro backend Python do usuário —
 * ver docstring de `GatewayMessage["review_job"]` (types.ts) pro porquê
 * de não esperar `type:"response"` como as requests HTTP comuns do
 * túnel. Chamado por gha-bot/routes.ts (POST /gha-bot/review). */
export async function dispatchReviewJob(
  env: Env,
  token: string,
  payload: { job_id: string; diff: string; metadata: Record<string, string> },
): Promise<{ delivered: boolean }> {
  const res = await routeToSession(
    new Request(`https://${GATEWAY_HOST}/_dispatch-job`, {
      method: "POST",
      headers: { ...internalHeaders(env), "Content-Type": "application/json" },
      body: JSON.stringify({ type: "review_job", ...payload }),
    }),
    token,
    env,
    new URL(`https://${GATEWAY_HOST}/_dispatch-job`),
  );
  if (!res.ok) return { delivered: false };
  return res.json();
}

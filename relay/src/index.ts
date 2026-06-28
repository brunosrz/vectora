import { verifyJwt, generateRelayToken } from "./auth";
import { RelaySession } from "./relay-session";
import type { Env, RegisterRequest, RegisterResponse } from "./types";

export { RelaySession };

const RELAY_HOST = "relay.vectora.chat";
const BASE_DOMAIN = "vectora.chat";

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    const host = url.hostname;

    // Subdomínio de sessão: {token}.vectora.chat
    if (host !== RELAY_HOST && host.endsWith(`.${BASE_DOMAIN}`)) {
      const token = host.slice(0, -`.${BASE_DOMAIN}`.length);
      return routeToSession(request, token, env, url);
    }

    // Endpoints do relay em relay.vectora.chat
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
        new Request(`https://${RELAY_HOST}/_health`, { method: "GET" }),
        token,
        env,
        url,
      );
    }

    if (
      request.method === "DELETE" &&
      url.pathname.startsWith("/relay/session/")
    ) {
      const token = url.pathname.slice("/relay/session/".length);
      if (!token) return new Response("Bad Request", { status: 400 });
      return routeToSession(
        new Request(`https://${RELAY_HOST}/_revoke`, { method: "DELETE" }),
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

async function handleRegister(request: Request, env: Env): Promise<Response> {
  let body: RegisterRequest;
  try {
    body = (await request.json()) as RegisterRequest;
  } catch {
    return new Response("Bad Request", { status: 400 });
  }

  if (!body.jwt || !body.fingerprint) {
    return new Response("Bad Request — jwt and fingerprint required", {
      status: 400,
    });
  }

  let userId: string;
  try {
    const payload = await verifyJwt(body.jwt, env.VECTORA_JWT_SECRET);
    userId = payload.sub;
  } catch (err) {
    return new Response(`Unauthorized — ${(err as Error).message}`, {
      status: 401,
    });
  }

  const token = await generateRelayToken(
    userId,
    body.fingerprint,
    env.RELAY_HMAC_SECRET,
  );
  const response: RegisterResponse = {
    token,
    subdomain: `${token}.${BASE_DOMAIN}`,
    websocket_url: `wss://${RELAY_HOST}/ws/${token}`,
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
  await env.RELAY_METRICS.put(`oauth:${body.state}`, body.token, {
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
  const token = await env.RELAY_METRICS.get(`oauth:${state}`);
  if (!token) return new Response("Pending", { status: 202 });
  await env.RELAY_METRICS.delete(`oauth:${state}`);
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
  const id = env.RELAY_SESSION.idFromName(token);
  const stub = env.RELAY_SESSION.get(id);
  return stub.fetch(request);
}

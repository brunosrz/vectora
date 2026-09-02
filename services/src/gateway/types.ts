import type { EmailMessage, JobMessage } from "../lib/queue-types";

export interface Env {
  GATEWAY_SESSION: DurableObjectNamespace;
  GATEWAY_METRICS: KVNamespace;
  VECTORA_APP_SECRET: string;
  // Nunca embutido em nenhum binário distribuído — só o Worker conhece este
  // valor. Prova que uma chamada a `/_health`, `/_revoke`, `/_set-secret`
  // veio do próprio gatewayHandler, não de um client externo batendo direto
  // no subdomínio `{token}.vectora.chat` com o VECTORA_APP_SECRET (esse sim
  // distribuído a toda instalação, então não serve pra provar origem interna).
  GATEWAY_INTERNAL_SECRET: string;
  GATEWAY_HMAC_SECRET: string;
  VECTORA_OAUTH_SECRET: string;
  GATEWAY_URL: string;
  MAX_PAYLOAD_BYTES: string;
  QUEUE_TTL_MS: string;
  TEST_IS_WINDOWS?: string;
  // updates/
  R2: R2Bucket;
  KV: KVNamespace;
  // auth/billing/license/gdpr/api-keys/issues
  DB: D1Database;
  APP_URL: string;
  RESEND_API_KEY: string;
  TURNSTILE_SECRET_KEY?: string;
  STRIPE_SECRET_KEY: string;
  STRIPE_WEBHOOK_SECRET: string;
  STRIPE_PRICE_PRO_USD: string;
  ASAAS_API_KEY: string;
  ASAAS_API_URL: string;
  ASAAS_WEBHOOK_SECRET: string;
  // queues
  EMAIL_QUEUE: Queue<EmailMessage>;
  JOBS_QUEUE: Queue<JobMessage>;
  // license
  LICENSE_VALIDATE_LIMITER: RateLimit;
  // auth/license — /auth/login, /license/agent-login
  AUTH_LOGIN_LIMITER: RateLimit;
  // gateway/index.ts — POST /register (token de app já defende, isto é
  // defesa em profundidade contra automação em massa).
  GATEWAY_LIMITER: RateLimit;
  // registry/discovery.ts — sem token, discovery de skills via GitHub code
  // search fica desligada (não é erro, ver discoverSkills).
  GITHUB_TOKEN?: string;
  // gha-bot/ — chave mestra AES-256-GCM (base64) pra cifrar/decifrar a
  // chave de provider de cada usuário (gha-bot/crypto.ts). Cloudflare
  // Secrets Store não serve aqui — ver comentário em crypto.ts.
  GHA_BOT_ENCRYPTION_KEY: string;
}

export interface RegisterRequest {
  fingerprint: string;
}

export interface RegisterResponse {
  token: string;
  subdomain: string;
  websocket_url: string;
  // Devolvido só nesta resposta — o Worker guarda apenas o hash (ver
  // hashConnectorSecret em auth.ts). Sem isto, o WS não abre (ver
  // GatewaySession::handleWebSocketUpgrade).
  connector_secret: string;
}

export interface QueuedRequest {
  id: string;
  method: string;
  path: string;
  headers: Record<string, string>;
  body: string;
  enqueuedAt: number;
}

// WebSocket protocol messages (gateway ↔ Python client)
export type GatewayMessage =
  | {
      type: "request";
      id: string;
      method: string;
      path: string;
      headers: Record<string, string>;
      body: string;
    }
  | { type: "queued"; items: QueuedRequest[] }
  | { type: "ping" }
  | { type: "health"; connected: boolean; queued: number };

export type ClientMessage =
  | {
      type: "response";
      id: string;
      status: number;
      headers: Record<string, string>;
      body: string;
    }
  | { type: "pong" };

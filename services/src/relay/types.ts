import type { EmailMessage, JobMessage } from "../lib/queue-types";

export interface Env {
  RELAY_SESSION: DurableObjectNamespace;
  RELAY_METRICS: KVNamespace;
  VECTORA_JWT_SECRET: string;
  RELAY_HMAC_SECRET: string;
  VECTORA_OAUTH_SECRET: string;
  RELAY_URL: string;
  MAX_PAYLOAD_BYTES: string;
  QUEUE_TTL_MS: string;
  TEST_IS_WINDOWS?: string;
  // updates/
  R2: R2Bucket;
  KV: KVNamespace;
  // auth/billing/license/gdpr/api-keys/issues (Fase B/C)
  DB: D1Database;
  APP_URL: string;
  RESEND_API_KEY: string;
  TURNSTILE_SECRET_KEY?: string;
  STRIPE_SECRET_KEY: string;
  STRIPE_WEBHOOK_SECRET: string;
  STRIPE_PRICE_PRO_USD: string;
  ASAAS_API_KEY: string;
  ASAAS_API_URL: string;
  // queues
  EMAIL_QUEUE: Queue<EmailMessage>;
  JOBS_QUEUE: Queue<JobMessage>;
}

export interface JwtPayload {
  sub: string;
  exp: number;
  iat: number;
}

export interface RegisterRequest {
  jwt: string;
  fingerprint: string;
}

export interface RegisterResponse {
  token: string;
  subdomain: string;
  websocket_url: string;
}

export interface QueuedRequest {
  id: string;
  method: string;
  path: string;
  headers: Record<string, string>;
  body: string;
  enqueuedAt: number;
}

// WebSocket protocol messages (relay ↔ Python client)
export type RelayMessage =
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

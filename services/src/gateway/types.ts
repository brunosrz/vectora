import type { EmailMessage, JobMessage } from "../lib/queue-types";

export interface Env {
  GATEWAY_SESSION: DurableObjectNamespace;
  GATEWAY_METRICS: KVNamespace;
  VECTORA_APP_SECRET: string;
  GATEWAY_HMAC_SECRET: string;
  VECTORA_OAUTH_SECRET: string;
  GATEWAY_URL: string;
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
  // license
  LICENSE_VALIDATE_LIMITER: RateLimit;
}

export interface RegisterRequest {
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

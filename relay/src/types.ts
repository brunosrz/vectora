export interface Env {
  RELAY_SESSION: DurableObjectNamespace;
  RELAY_METRICS: KVNamespace;
  VECTORA_JWT_SECRET: string;
  RELAY_HMAC_SECRET: string;
  VECTORA_OAUTH_SECRET: string;
  MAX_PAYLOAD_BYTES: string;
  QUEUE_TTL_MS: string;
  TEST_IS_WINDOWS?: string;
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

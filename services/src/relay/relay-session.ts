import type { Env, QueuedRequest, RelayMessage, ClientMessage } from "./types";

const QUEUE_TTL_DEFAULT = 600_000; // 10 min
const FORWARD_TIMEOUT_MS = 30_000;
const PING_INTERVAL_MS = 20_000;

interface PendingResponse {
  resolve: (msg: ClientMessage & { type: "response" }) => void;
  reject: (err: Error) => void;
  timer: ReturnType<typeof setTimeout>;
}

export class RelaySession implements DurableObject {
  private ws: WebSocket | null = null;
  private queue: QueuedRequest[] = [];
  private pending = new Map<string, PendingResponse>();
  private pingTimer: ReturnType<typeof setInterval> | null = null;
  private readonly ttlMs: number;

  constructor(
    private readonly state: DurableObjectState,
    private readonly env: Env,
  ) {
    this.ttlMs = parseInt(env.QUEUE_TTL_MS ?? String(QUEUE_TTL_DEFAULT), 10);
    this.state.blockConcurrencyWhile(async () => {
      this.queue =
        (await this.state.storage.get<QueuedRequest[]>("queue")) ?? [];
    });
  }

  async fetch(request: Request): Promise<Response> {
    const url = new URL(request.url);

    if (request.headers.get("Upgrade") === "websocket") {
      return this.handleWebSocketUpgrade(request);
    }

    const path = url.pathname;

    if (path === "/_health") {
      return Response.json({
        connected: this.ws !== null,
        queued: this.queue.length,
      });
    }

    if (path === "/_revoke" && request.method === "DELETE") {
      return this.handleRevoke();
    }

    return this.forwardToLocal(request);
  }

  private handleWebSocketUpgrade(_request: Request): Response {
    const pair = new WebSocketPair();
    const [client, server] = Object.values(pair) as [WebSocket, WebSocket];

    this.state.acceptWebSocket(server);
    this.replaceConnection(server);

    return new Response(null, { status: 101, webSocket: client });
  }

  private replaceConnection(ws: WebSocket): void {
    if (this.ws) {
      try {
        this.ws.close(1001, "replaced");
      } catch {
        /* ignore */
      }
    }
    this.ws = ws;

    if (this.pingTimer) clearInterval(this.pingTimer);
    this.pingTimer = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        const msg: RelayMessage = { type: "ping" };
        this.ws.send(JSON.stringify(msg));
      }
    }, PING_INTERVAL_MS);

    this.flushQueue();
  }

  async webSocketMessage(
    ws: WebSocket,
    message: string | ArrayBuffer,
  ): Promise<void> {
    if (typeof message !== "string") return;
    let parsed: ClientMessage;
    try {
      parsed = JSON.parse(message) as ClientMessage;
    } catch {
      return;
    }

    if (parsed.type === "response") {
      const pending = this.pending.get(parsed.id);
      if (pending) {
        clearTimeout(pending.timer);
        this.pending.delete(parsed.id);
        pending.resolve(parsed);
      }
    }
  }

  async webSocketClose(_ws: WebSocket): Promise<void> {
    this.ws = null;
    if (this.pingTimer) {
      clearInterval(this.pingTimer);
      this.pingTimer = null;
    }
    // Rejeita todos os pending em voo
    for (const [id, p] of this.pending) {
      clearTimeout(p.timer);
      p.reject(new Error("WebSocket closed"));
      this.pending.delete(id);
    }
  }

  async webSocketError(_ws: WebSocket, _error: unknown): Promise<void> {
    await this.webSocketClose(_ws);
  }

  private async forwardToLocal(request: Request): Promise<Response> {
    const maxBytes = parseInt(this.env.MAX_PAYLOAD_BYTES ?? "5242880", 10);
    const contentLength = parseInt(
      request.headers.get("content-length") ?? "0",
      10,
    );
    if (contentLength > maxBytes) {
      return new Response("Payload Too Large", { status: 413 });
    }

    const bodyBytes = await request.arrayBuffer();
    if (bodyBytes.byteLength > maxBytes) {
      return new Response("Payload Too Large", { status: 413 });
    }

    const bodyB64 = btoa(String.fromCharCode(...new Uint8Array(bodyBytes)));
    const headers: Record<string, string> = {};
    request.headers.forEach((v, k) => {
      headers[k] = v;
    });

    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      await this.enqueue(
        request.method,
        new URL(request.url).pathname,
        headers,
        bodyB64,
      );
      return new Response("Accepted — backend offline, request queued", {
        status: 202,
      });
    }

    const id = crypto.randomUUID();
    const msg: RelayMessage = {
      type: "request",
      id,
      method: request.method,
      path: new URL(request.url).pathname + new URL(request.url).search,
      headers,
      body: bodyB64,
    };

    return new Promise<Response>((resolve) => {
      const timer = setTimeout(() => {
        this.pending.delete(id);
        resolve(new Response("Gateway Timeout", { status: 504 }));
      }, FORWARD_TIMEOUT_MS);

      this.pending.set(id, {
        resolve: (resp) => {
          const respHeaders = new Headers(resp.headers);
          const respBody = Uint8Array.from(atob(resp.body), (c) =>
            c.charCodeAt(0),
          );
          resolve(
            new Response(respBody, {
              status: resp.status,
              headers: respHeaders,
            }),
          );
        },
        reject: () => resolve(new Response("Bad Gateway", { status: 502 })),
        timer,
      });

      this.ws!.send(JSON.stringify(msg));
    });
  }

  private async enqueue(
    method: string,
    path: string,
    headers: Record<string, string>,
    body: string,
  ): Promise<void> {
    const now = Date.now();
    this.queue = this.queue.filter((q) => now - q.enqueuedAt < this.ttlMs);
    this.queue.push({
      id: crypto.randomUUID(),
      method,
      path,
      headers,
      body,
      enqueuedAt: now,
    });
    await this.state.storage.put("queue", this.queue);
    await this.state.storage.setAlarm(now + this.ttlMs + 1000);
  }

  async alarm(): Promise<void> {
    const now = Date.now();
    this.queue = this.queue.filter((q) => now - q.enqueuedAt < this.ttlMs);
    await this.state.storage.put("queue", this.queue);
  }

  private flushQueue(): void {
    if (!this.ws || this.queue.length === 0) return;
    const msg: RelayMessage = { type: "queued", items: [...this.queue] };
    this.ws.send(JSON.stringify(msg));
    this.queue = [];
    void this.state.storage.put("queue", this.queue);
  }

  private handleRevoke(): Response {
    if (this.ws) {
      try {
        this.ws.close(1000, "revoked");
      } catch {
        /* ignore */
      }
      this.ws = null;
    }
    this.queue = [];
    // Persiste limpeza da fila na próxima escrita (próximo enqueue ou alarm)
    return Response.json({ revoked: true });
  }
}

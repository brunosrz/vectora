import { describe, it, expect } from "vitest";
import { env, SELF } from "cloudflare:test";
import type { Env } from "../src/types";

declare module "cloudflare:test" {
  interface ProvidedEnv extends Env {}
}

const now = Math.floor(Date.now() / 1000);

async function makeJwt(
  sub: string,
  secret: string,
  expOffset = 3600,
): Promise<string> {
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const esc = (s: string) =>
    s.replace(/[=+/]/g, (c) => ({ "=": "", "+": "-", "/": "_" })[c] ?? c);
  const header = esc(btoa(JSON.stringify({ alg: "HS256", typ: "JWT" })));
  const body = esc(
    btoa(JSON.stringify({ sub, exp: now + expOffset, iat: now })),
  );
  const sig = await crypto.subtle.sign(
    "HMAC",
    key,
    new TextEncoder().encode(`${header}.${body}`),
  );
  return `${header}.${body}.${esc(btoa(String.fromCharCode(...new Uint8Array(sig))))}`;
}

// Testes que só passam pelo Worker (sem tocar Durable Object) — rodam em todos OS.
describe("POST /register", () => {
  it("retorna token e subdomínio para JWT válido", async () => {
    const jwt = await makeJwt("user-abc", env.VECTORA_JWT_SECRET);
    const res = await SELF.fetch("https://relay.vectora.chat/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ jwt, fingerprint: "fp-test" }),
    });
    expect(res.status).toBe(200);
    const data = (await res.json()) as {
      token: string;
      subdomain: string;
      websocket_url: string;
    };
    expect(data.token).toMatch(/^[a-z0-9]{6}$/);
    expect(data.subdomain).toBe(`${data.token}.vectora.chat`);
    expect(data.websocket_url).toBe(
      `wss://relay.vectora.chat/ws/${data.token}`,
    );
  });

  it("retorna 401 para JWT inválido", async () => {
    const jwt = await makeJwt("user-abc", "wrong-secret-for-signing-jwt!!");
    const res = await SELF.fetch("https://relay.vectora.chat/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ jwt, fingerprint: "fp-test" }),
    });
    expect(res.status).toBe(401);
  });

  it("retorna 401 para JWT expirado", async () => {
    const jwt = await makeJwt("user-abc", env.VECTORA_JWT_SECRET, -1);
    const res = await SELF.fetch("https://relay.vectora.chat/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ jwt, fingerprint: "fp-test" }),
    });
    expect(res.status).toBe(401);
  });

  it("retorna 400 para body malformado", async () => {
    const res = await SELF.fetch("https://relay.vectora.chat/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: "not-json",
    });
    expect(res.status).toBe(400);
  });
});

// Verificação de payload é feita no Worker antes de criar o DO — sem SQLite.
describe("webhook — verificação de payload (Worker-level)", () => {
  it("retorna 413 para payload com content-length acima de 5MB", async () => {
    const res = await SELF.fetch("https://abc123.vectora.chat/webhooks/test", {
      method: "POST",
      headers: { "content-length": String(5 * 1024 * 1024 + 1) },
    });
    expect(res.status).toBe(413);
  });
});

// Testes que criam Durable Object (SQLite no disco). Em Windows, workerd não
// libera o lock do arquivo SQLite antes do cleanup do isolated storage (EBUSY).
// Passam em CI (Linux/Ubuntu). Referência: https://developers.cloudflare.com/workers/testing/vitest-integration/known-issues/#isolated-storage
const itDO = env.TEST_IS_WINDOWS === "1" ? it.skip : it;

describe("GET /health/{token}", () => {
  itDO("retorna connected=false para token sem WebSocket ativo", async () => {
    const res = await SELF.fetch("https://relay.vectora.chat/health/abc123");
    expect(res.status).toBe(200);
    const data = (await res.json()) as { connected: boolean; queued: number };
    expect(data.connected).toBe(false);
    expect(data.queued).toBe(0);
  });
});

describe("DELETE /relay/session/{token}", () => {
  itDO("retorna 200 ao revogar token existente", async () => {
    const res = await SELF.fetch(
      "https://relay.vectora.chat/relay/session/abc123",
      {
        method: "DELETE",
      },
    );
    expect(res.status).toBe(200);
  });
});

describe("webhook via subdomínio (Durable Object)", () => {
  itDO(
    "retorna 202 quando backend está offline (sem WebSocket ativo)",
    async () => {
      const res = await SELF.fetch(
        "https://abc123.vectora.chat/webhooks/github",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-GitHub-Event": "push",
          },
          body: JSON.stringify({ ref: "refs/heads/main" }),
        },
      );
      expect(res.status).toBe(202);
    },
  );
});

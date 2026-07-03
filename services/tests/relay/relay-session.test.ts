import { describe, it, expect } from "vitest";
import { env, SELF } from "cloudflare:test";

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

  it("retorna 400 quando falta jwt ou fingerprint", async () => {
    const res = await SELF.fetch("https://relay.vectora.chat/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ jwt: "only-jwt" }),
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

// Guard clauses antes de tocar o Durable Object (sem SQLite, roda em todos OS).
describe("guard clauses (Worker-level, antes do DO)", () => {
  it("GET /ws/ sem token → 400", async () => {
    const res = await SELF.fetch("https://relay.vectora.chat/ws/");
    expect(res.status).toBe(400);
  });

  it("GET /ws/{token} sem Upgrade: websocket → 426", async () => {
    const res = await SELF.fetch("https://relay.vectora.chat/ws/abc123");
    expect(res.status).toBe(426);
  });

  it("GET /health/ sem token → 400", async () => {
    const res = await SELF.fetch("https://relay.vectora.chat/health/");
    expect(res.status).toBe(400);
  });

  it("DELETE /relay/session/ sem token → 400", async () => {
    const res = await SELF.fetch("https://relay.vectora.chat/relay/session/", {
      method: "DELETE",
    });
    expect(res.status).toBe(400);
  });

  it("rota desconhecida → 404", async () => {
    const res = await SELF.fetch("https://relay.vectora.chat/nope");
    expect(res.status).toBe(404);
  });
});

describe("POST /oauth/token (device flow store)", () => {
  it("rejeita sem o secret certo, body malformado, e campos faltando", async () => {
    const unauthorized = await SELF.fetch(
      "https://relay.vectora.chat/oauth/token",
      { method: "POST", body: "{}" },
    );
    expect(unauthorized.status).toBe(401);

    const badJson = await SELF.fetch("https://relay.vectora.chat/oauth/token", {
      method: "POST",
      headers: { Authorization: "Bearer test-oauth-secret" },
      body: "not-json",
    });
    expect(badJson.status).toBe(400);

    const missingFields = await SELF.fetch(
      "https://relay.vectora.chat/oauth/token",
      {
        method: "POST",
        headers: {
          Authorization: "Bearer test-oauth-secret",
          "Content-Type": "application/json",
        },
        body: "{}",
      },
    );
    expect(missingFields.status).toBe(400);
  });

  it("armazena o token e o poll subsequente encontra e consome (uso único)", async () => {
    const store = await SELF.fetch("https://relay.vectora.chat/oauth/token", {
      method: "POST",
      headers: {
        Authorization: "Bearer test-oauth-secret",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ state: "state-1", token: "device-token" }),
    });
    expect(store.status).toBe(200);

    const poll = await SELF.fetch(
      "https://relay.vectora.chat/oauth/token/state-1",
      { headers: { Authorization: "Bearer test-oauth-secret" } },
    );
    expect(poll.status).toBe(200);
    expect(await poll.json()).toEqual({ token: "device-token" });

    // Consumido — segunda consulta não encontra mais (202 pending).
    const pollAgain = await SELF.fetch(
      "https://relay.vectora.chat/oauth/token/state-1",
      { headers: { Authorization: "Bearer test-oauth-secret" } },
    );
    expect(pollAgain.status).toBe(202);
  });

  it("poll rejeita sem o secret certo", async () => {
    const res = await SELF.fetch(
      "https://relay.vectora.chat/oauth/token/never-stored",
    );
    expect(res.status).toBe(401);
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

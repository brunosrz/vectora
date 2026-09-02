import { describe, it, expect } from "vitest";
import { env, SELF } from "cloudflare:test";

// Testes que só passam pelo Worker (sem tocar Durable Object) — rodam em todos OS.
describe("POST /register", () => {
  it("retorna token e subdomínio pra request autenticado com VECTORA_APP_SECRET", async () => {
    const res = await SELF.fetch("https://gateway.vectora.chat/register", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${env.VECTORA_APP_SECRET}`,
      },
      body: JSON.stringify({ fingerprint: "fp-test" }),
    });
    expect(res.status).toBe(200);
    const data = (await res.json()) as {
      token: string;
      subdomain: string;
      websocket_url: string;
      connector_secret: string;
    };
    expect(data.token).toMatch(/^[a-z0-9]{10}$/);
    expect(data.subdomain).toBe(`${data.token}.vectora.chat`);
    expect(data.websocket_url).toBe(
      `wss://gateway.vectora.chat/ws/${data.token}`,
    );
    expect(data.connector_secret).toMatch(/^[A-Za-z0-9_-]{43}$/);
  });

  it("retorna 401 sem o Authorization header", async () => {
    const res = await SELF.fetch("https://gateway.vectora.chat/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ fingerprint: "fp-test" }),
    });
    expect(res.status).toBe(401);
  });

  it("retorna 401 com VECTORA_APP_SECRET errado", async () => {
    const res = await SELF.fetch("https://gateway.vectora.chat/register", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: "Bearer secret-errado",
      },
      body: JSON.stringify({ fingerprint: "fp-test" }),
    });
    expect(res.status).toBe(401);
  });

  it("duas instalações diferentes com o MESMO VECTORA_APP_SECRET fixo autenticam (prova o fix da rodada anterior — JWT por-instalação nunca batia com um secret único)", async () => {
    const auth = { Authorization: `Bearer ${env.VECTORA_APP_SECRET}` };
    const first = await SELF.fetch("https://gateway.vectora.chat/register", {
      method: "POST",
      headers: { "Content-Type": "application/json", ...auth },
      body: JSON.stringify({ fingerprint: "fp-installation-1" }),
    });
    const second = await SELF.fetch("https://gateway.vectora.chat/register", {
      method: "POST",
      headers: { "Content-Type": "application/json", ...auth },
      body: JSON.stringify({ fingerprint: "fp-installation-2" }),
    });
    expect(first.status).toBe(200);
    expect(second.status).toBe(200);
  });

  it("retorna 400 para body malformado", async () => {
    const res = await SELF.fetch("https://gateway.vectora.chat/register", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${env.VECTORA_APP_SECRET}`,
      },
      body: "not-json",
    });
    expect(res.status).toBe(400);
  });

  it("retorna 400 quando falta fingerprint", async () => {
    const res = await SELF.fetch("https://gateway.vectora.chat/register", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${env.VECTORA_APP_SECRET}`,
      },
      body: JSON.stringify({}),
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
    const res = await SELF.fetch("https://gateway.vectora.chat/ws/");
    expect(res.status).toBe(400);
  });

  it("GET /ws/{token} sem Upgrade: websocket → 426", async () => {
    const res = await SELF.fetch("https://gateway.vectora.chat/ws/abc123");
    expect(res.status).toBe(426);
  });

  it("GET /health/ sem token → 400", async () => {
    const res = await SELF.fetch("https://gateway.vectora.chat/health/");
    expect(res.status).toBe(400);
  });

  it("DELETE /gateway/session/ sem token → 400", async () => {
    const res = await SELF.fetch(
      "https://gateway.vectora.chat/gateway/session/",
      { method: "DELETE" },
    );
    expect(res.status).toBe(400);
  });

  it("rota desconhecida → 404", async () => {
    const res = await SELF.fetch("https://gateway.vectora.chat/nope");
    expect(res.status).toBe(404);
  });
});

describe("POST /oauth/token (device flow store)", () => {
  it("rejeita sem o secret certo, body malformado, e campos faltando", async () => {
    const unauthorized = await SELF.fetch(
      "https://gateway.vectora.chat/oauth/token",
      { method: "POST", body: "{}" },
    );
    expect(unauthorized.status).toBe(401);

    const badJson = await SELF.fetch(
      "https://gateway.vectora.chat/oauth/token",
      {
        method: "POST",
        headers: { Authorization: "Bearer test-oauth-secret" },
        body: "not-json",
      },
    );
    expect(badJson.status).toBe(400);

    const missingFields = await SELF.fetch(
      "https://gateway.vectora.chat/oauth/token",
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
    const store = await SELF.fetch("https://gateway.vectora.chat/oauth/token", {
      method: "POST",
      headers: {
        Authorization: "Bearer test-oauth-secret",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ state: "state-1", token: "device-token" }),
    });
    expect(store.status).toBe(200);

    const poll = await SELF.fetch(
      "https://gateway.vectora.chat/oauth/token/state-1",
      { headers: { Authorization: "Bearer test-oauth-secret" } },
    );
    expect(poll.status).toBe(200);
    expect(await poll.json()).toEqual({ token: "device-token" });

    // Consumido — segunda consulta não encontra mais (202 pending).
    const pollAgain = await SELF.fetch(
      "https://gateway.vectora.chat/oauth/token/state-1",
      { headers: { Authorization: "Bearer test-oauth-secret" } },
    );
    expect(pollAgain.status).toBe(202);
  });

  it("poll rejeita sem o secret certo", async () => {
    const res = await SELF.fetch(
      "https://gateway.vectora.chat/oauth/token/never-stored",
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
    const res = await SELF.fetch("https://gateway.vectora.chat/health/abc123");
    expect(res.status).toBe(200);
    const data = (await res.json()) as { connected: boolean; queued: number };
    expect(data.connected).toBe(false);
    expect(data.queued).toBe(0);
  });
});

describe("DELETE /gateway/session/{token}", () => {
  itDO("retorna 200 ao revogar token existente", async () => {
    const res = await SELF.fetch(
      "https://gateway.vectora.chat/gateway/session/abc123",
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

describe("achado de segurança: rotas de controle (_health/_revoke) não são alcançáveis direto pelo subdomínio", () => {
  itDO(
    "GET direto em {token}.vectora.chat/_health não devolve o JSON de status — cai como request tunelado comum (202, sem client conectado)",
    async () => {
      const res = await SELF.fetch("https://abc123.vectora.chat/_health");
      expect(res.status).toBe(202);
    },
  );

  itDO(
    "DELETE direto em {token}.vectora.chat/_revoke não revoga a sessão — cai como request tunelado comum",
    async () => {
      const res = await SELF.fetch("https://abc123.vectora.chat/_revoke", {
        method: "DELETE",
      });
      // Nunca o 200 estruturado de handleRevoke — sem client conectado,
      // forwardToLocal enfileira (202) em vez de aceitar como comando.
      expect(res.status).toBe(202);
    },
  );

  itDO(
    "a rota oficial gateway.vectora.chat/health/{token} continua funcionando normalmente",
    async () => {
      const res = await SELF.fetch(
        "https://gateway.vectora.chat/health/abc123",
      );
      expect(res.status).toBe(200);
      const data = (await res.json()) as { connected: boolean };
      expect(data.connected).toBe(false);
    },
  );
});

describe("achado de segurança: WebSocket exige o connector_secret quando um já foi emitido", () => {
  itDO(
    "abrir /ws/{token} sem Authorization, depois de /register já ter emitido um secret → 401",
    async () => {
      const register = await SELF.fetch(
        "https://gateway.vectora.chat/register",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${env.VECTORA_APP_SECRET}`,
          },
          body: JSON.stringify({ fingerprint: "fp-ws-sem-secret" }),
        },
      );
      const { token } = (await register.json()) as { token: string };

      const res = await SELF.fetch(`https://gateway.vectora.chat/ws/${token}`, {
        headers: { Upgrade: "websocket" },
      });
      expect(res.status).toBe(401);
    },
  );

  itDO("abrir /ws/{token} com Authorization errado → 401", async () => {
    const register = await SELF.fetch("https://gateway.vectora.chat/register", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${env.VECTORA_APP_SECRET}`,
      },
      body: JSON.stringify({ fingerprint: "fp-ws-secret-errado" }),
    });
    const { token } = (await register.json()) as { token: string };

    const res = await SELF.fetch(`https://gateway.vectora.chat/ws/${token}`, {
      headers: {
        Upgrade: "websocket",
        Authorization: "Bearer secret-que-nao-e-o-certo",
      },
    });
    expect(res.status).toBe(401);
  });

  itDO(
    "abrir /ws/{token} com o connector_secret certo → aceita o upgrade (par de acerto)",
    async () => {
      const register = await SELF.fetch(
        "https://gateway.vectora.chat/register",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${env.VECTORA_APP_SECRET}`,
          },
          body: JSON.stringify({ fingerprint: "fp-ws-secret-certo" }),
        },
      );
      const { token, connector_secret } = (await register.json()) as {
        token: string;
        connector_secret: string;
      };

      const res = await SELF.fetch(`https://gateway.vectora.chat/ws/${token}`, {
        headers: {
          Upgrade: "websocket",
          Authorization: `Bearer ${connector_secret}`,
        },
      });
      expect(res.status).toBe(101);
    },
  );

  itDO(
    "sem /register prévio (secretHash nunca setado) — upgrade rejeitado mesmo sem Authorization",
    async () => {
      const res = await SELF.fetch(
        "https://gateway.vectora.chat/ws/token-nunca-registrado",
        { headers: { Upgrade: "websocket" } },
      );
      expect(res.status).toBe(401);
    },
  );

  itDO(
    "sem /register prévio (secretHash nunca setado) — upgrade rejeitado mesmo com Authorization presente",
    async () => {
      const res = await SELF.fetch(
        "https://gateway.vectora.chat/ws/outro-token-nunca-registrado",
        {
          headers: {
            Upgrade: "websocket",
            Authorization: "Bearer qualquer-coisa",
          },
        },
      );
      expect(res.status).toBe(401);
    },
  );
});

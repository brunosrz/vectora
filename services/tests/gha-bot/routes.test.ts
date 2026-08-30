import { env } from "cloudflare:test";
import { describe, expect, it } from "vitest";
import { ghaBot } from "../../src/gha-bot/routes";
import { createSession } from "../../src/auth/session";

async function makeUserWithSession() {
  const userId = crypto.randomUUID();
  await env.DB.prepare(
    "INSERT INTO users (id, email, password_hash) VALUES (?, ?, ?)",
  )
    .bind(userId, `${userId}@example.com`, "pbkdf2$1$AA==$AA==")
    .run();
  const session = await createSession(env.DB, userId);
  return { userId, token: session.token };
}

describe("gha-bot tokens", () => {
  it("creates, lists, and revokes a token scoped to its owner", async () => {
    const { token } = await makeUserWithSession();
    const auth = {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    };

    const created = await ghaBot.request(
      "/tokens",
      { method: "POST", headers: auth, body: JSON.stringify({}) },
      env,
    );
    expect(created.status).toBe(200);
    const { secret } = await created.json<{ secret: string }>();
    expect(secret).toBeTruthy();

    const list = await ghaBot.request("/tokens", { headers: auth }, env);
    const tokens =
      await list.json<Array<{ id: string; revoked_at: string | null }>>();
    expect(tokens).toHaveLength(1);
    expect(tokens[0]!.revoked_at).toBeNull();

    const revoke = await ghaBot.request(
      `/tokens/${tokens[0]!.id}/revoke`,
      { method: "POST", headers: auth },
      env,
    );
    expect(revoke.status).toBe(200);

    // Erro/borda: revogar de novo não acha linha ainda-não-revogada.
    const revokeAgain = await ghaBot.request(
      `/tokens/${tokens[0]!.id}/revoke`,
      { method: "POST", headers: auth },
      env,
    );
    expect(revokeAgain.status).toBe(404);
  });

  it("rejects unauthenticated requests", async () => {
    const list = await ghaBot.request("/tokens", {}, env);
    expect(list.status).toBe(401);

    const create = await ghaBot.request(
      "/tokens",
      { method: "POST", body: "{}" },
      env,
    );
    expect(create.status).toBe(401);
  });

  it("scopes tokens per user — one user never sees another's tokens", async () => {
    const { token: tokenA } = await makeUserWithSession();
    const { token: tokenB } = await makeUserWithSession();

    await ghaBot.request(
      "/tokens",
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${tokenA}`,
          "Content-Type": "application/json",
        },
        body: "{}",
      },
      env,
    );

    const listB = await ghaBot.request(
      "/tokens",
      { headers: { Authorization: `Bearer ${tokenB}` } },
      env,
    );
    expect(await listB.json()).toEqual([]);
  });
});

describe("gha-bot settings", () => {
  it("returns null before any config is saved, then round-trips a PUT", async () => {
    const { token } = await makeUserWithSession();
    const auth = {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    };

    const before = await ghaBot.request("/settings", { headers: auth }, env);
    expect(await before.json()).toBeNull();

    const put = await ghaBot.request(
      "/settings",
      {
        method: "PUT",
        headers: auth,
        body: JSON.stringify({
          provider: "anthropic",
          model: "claude-sonnet-5",
          provider_api_key: "gha-bot-anthropic-key-abc",
          review_style: "strict",
        }),
      },
      env,
    );
    expect(put.status).toBe(200);

    const after = await ghaBot.request("/settings", { headers: auth }, env);
    const settings = await after.json<{
      provider: string;
      model: string;
      review_style: string;
    }>();
    expect(settings.provider).toBe("anthropic");
    expect(settings.model).toBe("claude-sonnet-5");
    expect(settings.review_style).toBe("strict");
    // A chave/referência nunca volta na resposta do painel.
    expect(settings).not.toHaveProperty("provider_api_key");
  });

  it("rejects missing fields and an invalid review_style — erro/borda", async () => {
    const { token } = await makeUserWithSession();
    const auth = {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    };

    const missing = await ghaBot.request(
      "/settings",
      {
        method: "PUT",
        headers: auth,
        body: JSON.stringify({ provider: "anthropic" }),
      },
      env,
    );
    expect(missing.status).toBe(400);

    const badStyle = await ghaBot.request(
      "/settings",
      {
        method: "PUT",
        headers: auth,
        body: JSON.stringify({
          provider: "anthropic",
          model: "claude-sonnet-5",
          provider_api_key: "ref",
          review_style: "chaotic",
        }),
      },
      env,
    );
    expect(badStyle.status).toBe(400);
  });

  it("a second PUT overwrites the first, not a duplicate row", async () => {
    const { token, userId } = await makeUserWithSession();
    const auth = {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    };

    for (const model of ["claude-sonnet-5", "claude-opus-5"]) {
      await ghaBot.request(
        "/settings",
        {
          method: "PUT",
          headers: auth,
          body: JSON.stringify({
            provider: "anthropic",
            model,
            provider_api_key: "ref",
          }),
        },
        env,
      );
    }

    const { results } = await env.DB.prepare(
      "SELECT model FROM gha_bot_config WHERE user_id = ?",
    )
      .bind(userId)
      .all<{ model: string }>();
    expect(results).toHaveLength(1);
    expect(results[0]!.model).toBe("claude-opus-5");
  });
});

describe("gha-bot config (Action pública, autenticada por VECTORA_BOT_TOKEN)", () => {
  async function makeProUserWithBotToken() {
    const { userId, token: sessionToken } = await makeUserWithSession();
    await env.DB.prepare(
      "INSERT INTO subscriptions (id, user_id, tier, status) VALUES (?, ?, 'pro', 'active')",
    )
      .bind(crypto.randomUUID(), userId)
      .run();

    const created = await ghaBot.request(
      "/tokens",
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${sessionToken}`,
          "Content-Type": "application/json",
        },
        body: "{}",
      },
      env,
    );
    const { secret: botToken } = await created.json<{ secret: string }>();
    return { userId, sessionToken, botToken };
  }

  it("devolve a chave real (decifrada) pra um usuário Pro configurado", async () => {
    const { sessionToken, botToken } = await makeProUserWithBotToken();

    await ghaBot.request(
      "/settings",
      {
        method: "PUT",
        headers: {
          Authorization: `Bearer ${sessionToken}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          provider: "anthropic",
          model: "claude-sonnet-5",
          provider_api_key: "sk-ant-super-secreta-de-verdade",
          review_style: "lenient",
        }),
      },
      env,
    );

    const res = await ghaBot.request(
      "/config",
      { headers: { Authorization: `Bearer ${botToken}` } },
      env,
    );
    expect(res.status).toBe(200);
    const config = await res.json<{
      provider: string;
      model: string;
      api_key: string;
      review_style: string;
    }>();
    expect(config).toEqual({
      provider: "anthropic",
      model: "claude-sonnet-5",
      api_key: "sk-ant-super-secreta-de-verdade",
      review_style: "lenient",
    });
  });

  it("rejeita token inválido/revogado — erro/borda", async () => {
    const unknown = await ghaBot.request(
      "/config",
      { headers: { Authorization: "Bearer token-que-nao-existe" } },
      env,
    );
    expect(unknown.status).toBe(401);

    const { sessionToken, botToken } = await makeProUserWithBotToken();
    const listed = await ghaBot.request(
      "/tokens",
      { headers: { Authorization: `Bearer ${sessionToken}` } },
      env,
    );
    const listedTokens = await listed.json<Array<{ id: string }>>();
    const id = listedTokens[0]!.id;
    await ghaBot.request(
      `/tokens/${id}/revoke`,
      { method: "POST", headers: { Authorization: `Bearer ${sessionToken}` } },
      env,
    );

    const revoked = await ghaBot.request(
      "/config",
      { headers: { Authorization: `Bearer ${botToken}` } },
      env,
    );
    expect(revoked.status).toBe(401);
  });

  it("rejeita usuário sem Pro, mesmo com token válido e config salva — erro/borda", async () => {
    const { userId, token: sessionToken } = await makeUserWithSession();
    const auth = {
      Authorization: `Bearer ${sessionToken}`,
      "Content-Type": "application/json",
    };
    await ghaBot.request(
      "/settings",
      {
        method: "PUT",
        headers: auth,
        body: JSON.stringify({
          provider: "anthropic",
          model: "claude-sonnet-5",
          provider_api_key: "sk-ant-x",
        }),
      },
      env,
    );
    const created = await ghaBot.request(
      "/tokens",
      { method: "POST", headers: auth, body: "{}" },
      env,
    );
    const { secret: botToken } = await created.json<{ secret: string }>();
    void userId;

    const res = await ghaBot.request(
      "/config",
      { headers: { Authorization: `Bearer ${botToken}` } },
      env,
    );
    expect(res.status).toBe(403);
    expect(await res.json()).toEqual({ error: "pro_required" });
  });

  it("devolve not_configured pra usuário Pro sem settings salvas ainda — erro/borda", async () => {
    const { botToken } = await makeProUserWithBotToken();

    const res = await ghaBot.request(
      "/config",
      { headers: { Authorization: `Bearer ${botToken}` } },
      env,
    );
    expect(res.status).toBe(404);
  });
});

/** gha-bot/ — Vectora Bot for GHA: painel (sessão) + Action pública (token). */
import { Hono } from "hono";
import type { Env } from "../gateway/types";
import { requireUserId } from "../auth/routes";
import { sha256Hex } from "../auth/session";

export const ghaBot = new Hono<{ Bindings: Env }>();

const VALID_REVIEW_STYLES = new Set(["strict", "balanced", "lenient"]);

ghaBot.get("/tokens", async (c) => {
  const userId = await requireUserId(c);
  if (!userId) return c.json({ error: "unauthorized" }, 401);

  const { results } = await c.env.DB.prepare(
    "SELECT id, repo_scope, created_at, revoked_at FROM gha_bot_tokens WHERE user_id = ? ORDER BY created_at DESC",
  )
    .bind(userId)
    .all<{
      id: string;
      repo_scope: string | null;
      created_at: string;
      revoked_at: string | null;
    }>();

  return c.json(results);
});

ghaBot.post("/tokens", async (c) => {
  const userId = await requireUserId(c);
  if (!userId) return c.json({ error: "unauthorized" }, 401);

  const body = await c.req
    .json<{ repo_scope?: string }>()
    .catch(() => ({}) as { repo_scope?: string });

  const raw = crypto.randomUUID();
  const hash = await sha256Hex(raw);

  await c.env.DB.prepare(
    "INSERT INTO gha_bot_tokens (id, user_id, token_hash, repo_scope) VALUES (?, ?, ?, ?)",
  )
    .bind(crypto.randomUUID(), userId, hash, body.repo_scope ?? null)
    .run();

  // Mostrado uma vez só — só o hash fica salvo, igual api_keys.
  return c.json({ secret: raw });
});

ghaBot.post("/tokens/:id/revoke", async (c) => {
  const userId = await requireUserId(c);
  if (!userId) return c.json({ error: "unauthorized" }, 401);

  const id = c.req.param("id");
  const result = await c.env.DB.prepare(
    "UPDATE gha_bot_tokens SET revoked_at = datetime('now') WHERE id = ? AND user_id = ? AND revoked_at IS NULL",
  )
    .bind(id, userId)
    .run();

  if (result.meta.changes === 0) return c.json({ error: "not_found" }, 404);
  return c.json({ ok: true });
});

ghaBot.get("/settings", async (c) => {
  const userId = await requireUserId(c);
  if (!userId) return c.json({ error: "unauthorized" }, 401);

  const row = await c.env.DB.prepare(
    "SELECT provider, model, review_style, updated_at FROM gha_bot_config WHERE user_id = ?",
  )
    .bind(userId)
    .first<{
      provider: string;
      model: string;
      review_style: string;
      updated_at: string;
    }>();

  // Chave de provider NUNCA volta pro painel — só o nome da secret_ref é
  // gerenciado, o valor em si só é lido em GET /gha-bot/config (pela Action,
  // via token, não pela sessão do painel).
  return c.json(row ?? null);
});

ghaBot.put("/settings", async (c) => {
  const userId = await requireUserId(c);
  if (!userId) return c.json({ error: "unauthorized" }, 401);

  const body = await c.req.json<{
    provider?: string;
    model?: string;
    provider_api_key_secret_ref?: string;
    review_style?: string;
  }>();

  if (!body.provider || !body.model || !body.provider_api_key_secret_ref) {
    return c.json({ error: "missing_fields" }, 400);
  }
  const reviewStyle = body.review_style ?? "balanced";
  if (!VALID_REVIEW_STYLES.has(reviewStyle)) {
    return c.json({ error: "invalid_review_style" }, 400);
  }

  await c.env.DB.prepare(
    `INSERT INTO gha_bot_config (user_id, provider, model, provider_api_key_secret_ref, review_style, updated_at)
     VALUES (?, ?, ?, ?, ?, datetime('now'))
     ON CONFLICT (user_id) DO UPDATE SET
       provider = excluded.provider,
       model = excluded.model,
       provider_api_key_secret_ref = excluded.provider_api_key_secret_ref,
       review_style = excluded.review_style,
       updated_at = datetime('now')`,
  )
    .bind(
      userId,
      body.provider,
      body.model,
      body.provider_api_key_secret_ref,
      reviewStyle,
    )
    .run();

  return c.json({ ok: true });
});

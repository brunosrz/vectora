/** api-keys/ — porta company/src/server/fns/api-keys.ts. */
import { Hono } from "hono";
import type { Env } from "../relay/types";
import { requireUserId } from "../auth/routes";
import { getUserRole } from "../auth/roles";
import { sha256Hex } from "../auth/session";

export const apiKeys = new Hono<{ Bindings: Env }>();

const VALID_SCOPES = new Set(["read", "write", "admin"]);

apiKeys.get("/", async (c) => {
  const userId = await requireUserId(c);
  if (!userId) return c.json({ error: "unauthorized" }, 401);

  const { results } = await c.env.DB.prepare(
    "SELECT id, name, scopes, created_at, last_used_at FROM api_keys WHERE user_id = ? ORDER BY created_at DESC",
  )
    .bind(userId)
    .all<{
      id: string;
      name: string;
      scopes: string;
      created_at: string;
      last_used_at: string | null;
    }>();

  return c.json(results.map((r) => ({ ...r, scopes: JSON.parse(r.scopes) })));
});

apiKeys.post("/", async (c) => {
  const userId = await requireUserId(c);
  if (!userId) return c.json({ error: "unauthorized" }, 401);

  const body = await c.req.json<{ name?: string; scopes?: string[] }>();
  if (!body.name || body.name.length < 1 || body.name.length > 64) {
    return c.json({ error: "invalid_name" }, 400);
  }
  const scopes = body.scopes ?? [];
  if (!scopes.length || !scopes.every((s) => VALID_SCOPES.has(s))) {
    return c.json({ error: "invalid_scopes" }, 400);
  }
  // O scope "admin" só pode ser concedido a quem já tem role=admin no D1 —
  // sem isso, qualquer usuário autenticado podia pedir uma key com scope
  // admin e o worker só validava o FORMATO do array, nunca o privilégio de
  // quem pedia (regra 8 CLAUDE.md: backend é fonte de verdade).
  if (scopes.includes("admin")) {
    const role = await getUserRole(c.env, userId);
    if (role !== "admin") {
      return c.json({ error: "admin_scope_forbidden" }, 403);
    }
  }

  const raw = crypto.randomUUID();
  const hash = await sha256Hex(raw);

  try {
    await c.env.DB.prepare(
      "INSERT INTO api_keys (id, user_id, name, scopes, key_hash) VALUES (?, ?, ?, ?, ?)",
    )
      .bind(
        crypto.randomUUID(),
        userId,
        body.name,
        JSON.stringify(scopes),
        hash,
      )
      .run();
  } catch {
    return c.json({ error: "name_taken" }, 409);
  }

  return c.json({ secret: `vk_${raw}` });
});

apiKeys.post("/:id/revoke", async (c) => {
  const userId = await requireUserId(c);
  if (!userId) return c.json({ error: "unauthorized" }, 401);

  const id = c.req.param("id");
  const result = await c.env.DB.prepare(
    "DELETE FROM api_keys WHERE id = ? AND user_id = ?",
  )
    .bind(id, userId)
    .run();

  if (result.meta.changes === 0) return c.json({ error: "not_found" }, 404);
  return c.json({ ok: true });
});

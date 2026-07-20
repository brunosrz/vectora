/** profile/ — porta company/src/server/fns/profile.ts (updateProfile). */
import { Hono } from "hono";
import type { Env } from "../gateway/types";
import { requireUserId } from "../auth/routes";

export const profile = new Hono<{ Bindings: Env }>();

profile.post("/update", async (c) => {
  const userId = await requireUserId(c);
  if (!userId) return c.json({ error: "unauthorized" }, 401);

  const body = await c.req.json<{
    full_name?: string;
    country?: "BR" | "INTL";
    language?: string;
  }>();

  const sets: string[] = ["updated_at = ?"];
  const binds: unknown[] = [new Date().toISOString()];

  if (body.full_name !== undefined) {
    if (body.full_name.length < 2 || body.full_name.length > 100) {
      return c.json({ error: "invalid_full_name" }, 400);
    }
    sets.push("full_name = ?");
    binds.push(body.full_name);
  }
  if (body.country !== undefined) {
    if (body.country !== "BR" && body.country !== "INTL") {
      return c.json({ error: "invalid_country" }, 400);
    }
    sets.push("country = ?");
    binds.push(body.country);
  }
  if (body.language !== undefined) {
    if (body.language.length < 2 || body.language.length > 10) {
      return c.json({ error: "invalid_language" }, 400);
    }
    sets.push("language = ?");
    binds.push(body.language);
  }

  binds.push(userId);
  await c.env.DB.prepare(`UPDATE users SET ${sets.join(", ")} WHERE id = ?`)
    .bind(...binds)
    .run();

  return c.json({ ok: true });
});

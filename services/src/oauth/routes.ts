/**
 * oauth/ — porta company/src/server/fns/oauth.ts (authorizeDevice). O gateway
 * (ex-relay) roda no mesmo Worker (ver src/gateway/), mas continua exposto só
 * via HTTP em gateway.vectora.chat — chamamos por fetch normal, não por
 * acesso direto ao módulo, pra não acoplar o dispatch por hostname a uma
 * chamada interna.
 */
import { Hono } from "hono";
import type { Env } from "../gateway/types";
import { requireUserId } from "../auth/routes";

export const oauth = new Hono<{ Bindings: Env }>();

oauth.post("/device", async (c) => {
  const userId = await requireUserId(c);
  if (!userId) return c.json({ error: "unauthorized" }, 401);

  const body = await c.req.json<{ state?: string }>();
  if (!body.state) return c.json({ error: "state_required" }, 400);

  const row = await c.env.DB.prepare(
    "SELECT token FROM tokens WHERE user_id = ?",
  )
    .bind(userId)
    .first<{ token: string | null }>();
  if (!row?.token) return c.json({ error: "no_token" }, 409);

  const resp = await fetch(`${c.env.GATEWAY_URL}/oauth/token`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${c.env.VECTORA_OAUTH_SECRET}`,
    },
    body: JSON.stringify({ state: body.state, token: row.token }),
  });
  if (!resp.ok) return c.json({ error: "gateway_error" }, 502);

  return c.json({ ok: true });
});

/**
 * Rota de integrações e OAuth — proxy REST para o handler de OAuth do Vectora.
 *
 * Repassa cookies do browser → backend para validação de auth.
 */

import { Hono } from "hono";

const VECTORA_API_URL = process.env.VECTORA_API_URL ?? "http://localhost:8080";

const integrations = new Hono();

function baseHeaders(cookies?: string): HeadersInit {
  return {
    "Content-Type": "application/json",
    ...(cookies ? { Cookie: cookies } : {}),
  };
}

/** GET /api/integrations — lista todas com status */
integrations.get("/", async (c) => {
  try {
    const res = await fetch(`${VECTORA_API_URL}/integrations`, {
      headers: baseHeaders(c.req.header("Cookie")),
    });
    return c.json(await res.json(), res.status as 200);
  } catch (err) {
    return c.json({ error: String(err) }, 502);
  }
});

/** POST /api/integrations/:id/verify — testa se a chave é válida */
integrations.post("/:id/verify", async (c) => {
  const id = c.req.param("id");
  try {
    const res = await fetch(`${VECTORA_API_URL}/integrations/${id}/verify`, {
      method: "POST",
      headers: baseHeaders(c.req.header("Cookie")),
    });
    return c.json(await res.json(), res.status as 200);
  } catch (err) {
    return c.json({ error: String(err) }, 502);
  }
});

/** GET /api/integrations/github/status */
integrations.get("/github/status", async (c) => {
  try {
    const res = await fetch(`${VECTORA_API_URL}/auth/github/status`, {
      headers: baseHeaders(c.req.header("Cookie")),
    });
    return c.json(await res.json(), res.status as 200);
  } catch (err) {
    return c.json({ connected: false, username: null }, 200);
  }
});

/** DELETE /api/integrations/github — desconecta */
integrations.delete("/github", async (c) => {
  try {
    const res = await fetch(`${VECTORA_API_URL}/auth/github`, {
      method: "DELETE",
      headers: baseHeaders(c.req.header("Cookie")),
    });
    return c.json(await res.json(), res.status as 200);
  } catch (err) {
    return c.json({ error: String(err) }, 502);
  }
});

export default integrations;

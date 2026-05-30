/**
 * Rota de tools — proxy para a política de tools do usuário (Bloco S, S5).
 *
 * GET /api/tools/policy → tools desabilitadas + lista de built-ins
 * PUT /api/tools/policy → define as tools desabilitadas do usuário
 */

import { Hono } from "hono";

const VECTORA_API_URL = process.env.VECTORA_API_URL ?? "http://localhost:8080";

const tools = new Hono();

function headers(cookies?: string): Record<string, string> {
  return {
    "Content-Type": "application/json",
    ...(cookies ? { Cookie: cookies } : {}),
  };
}

tools.get("/policy", async (c) => {
  try {
    const res = await fetch(`${VECTORA_API_URL}/tools/policy`, {
      headers: headers(c.req.header("Cookie")),
    });
    return c.json(await res.json(), res.status as 200);
  } catch {
    return c.json({ status: "error", message: "Backend indisponível" }, 503);
  }
});

tools.put("/policy", async (c) => {
  const body = await c.req.json();
  try {
    const res = await fetch(`${VECTORA_API_URL}/tools/policy`, {
      method: "PUT",
      headers: headers(c.req.header("Cookie")),
      body: JSON.stringify(body),
    });
    return c.json(await res.json(), res.status as 200);
  } catch {
    return c.json({ status: "error", message: "Backend indisponível" }, 503);
  }
});

export default tools;

/**
 * Proxy Hono para o handler de licença do backend.
 *
 * GET  /api/license/status — público (lê cache local do Launcher).
 * POST /api/license/portal — autenticado (cria sessão Stripe/Asaas portal).
 */

import { Hono } from "hono";

const VECTORA_API_URL = process.env.VECTORA_API_URL ?? "http://localhost:8080";

const license = new Hono();

function headers(cookies?: string): Record<string, string> {
  return {
    "Content-Type": "application/json",
    ...(cookies ? { Cookie: cookies } : {}),
  };
}

license.get("/status", async (c) => {
  try {
    const res = await fetch(`${VECTORA_API_URL}/license/status`, {
      headers: headers(c.req.header("Cookie")),
    });
    return c.json(await res.json(), res.status as 200);
  } catch {
    return c.json(
      {
        configured: false,
        tier: null,
        status: "offline",
        days_remaining: 0,
        expires_at: "",
        cached: false,
      },
      503,
    );
  }
});

license.post("/portal", async (c) => {
  try {
    const res = await fetch(`${VECTORA_API_URL}/license/portal`, {
      method: "POST",
      headers: headers(c.req.header("Cookie")),
      body: JSON.stringify({}),
    });
    return c.json(await res.json(), res.status as 200);
  } catch {
    return c.json({ detail: "Backend indisponível" }, 503);
  }
});

export default license;

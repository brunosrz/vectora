/**
 * Rota de plugins — proxy REST para o handler de plugins MCP do Vectora (Bloco S).
 *
 * GET    /api/plugins              → lista servidores MCP do usuário
 * POST   /api/plugins              → adiciona/atualiza um servidor
 * DELETE /api/plugins/:name        → remove um servidor
 * POST   /api/plugins/:name/verify → health-check
 */

import { Hono } from "hono";

const VECTORA_API_URL = process.env.VECTORA_API_URL ?? "http://localhost:8080";

const plugins = new Hono();

function headers(cookies?: string): Record<string, string> {
  return {
    "Content-Type": "application/json",
    ...(cookies ? { Cookie: cookies } : {}),
  };
}

plugins.get("/", async (c) => {
  try {
    const res = await fetch(`${VECTORA_API_URL}/plugins`, {
      headers: headers(c.req.header("Cookie")),
    });
    return c.json(await res.json(), res.status as 200);
  } catch {
    return c.json({ status: "error", message: "Backend indisponível" }, 503);
  }
});

plugins.post("/", async (c) => {
  const body = await c.req.json();
  try {
    const res = await fetch(`${VECTORA_API_URL}/plugins`, {
      method: "POST",
      headers: headers(c.req.header("Cookie")),
      body: JSON.stringify(body),
    });
    return c.json(await res.json(), res.status as 200);
  } catch {
    return c.json({ status: "error", message: "Backend indisponível" }, 503);
  }
});

plugins.delete("/:name", async (c) => {
  try {
    const res = await fetch(
      `${VECTORA_API_URL}/plugins/${encodeURIComponent(c.req.param("name"))}`,
      { method: "DELETE", headers: headers(c.req.header("Cookie")) },
    );
    return c.json(await res.json(), res.status as 200);
  } catch {
    return c.json({ status: "error", message: "Backend indisponível" }, 503);
  }
});

plugins.post("/:name/verify", async (c) => {
  try {
    const res = await fetch(
      `${VECTORA_API_URL}/plugins/${encodeURIComponent(c.req.param("name"))}/verify`,
      { method: "POST", headers: headers(c.req.header("Cookie")) },
    );
    return c.json(await res.json(), res.status as 200);
  } catch {
    return c.json({ ok: false, tools: [], error: "Backend indisponível" }, 503);
  }
});

export default plugins;

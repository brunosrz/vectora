/**
 * Rota de skills — proxy REST para o handler de skills do Vectora (S8).
 *
 * GET    /api/skills              → lista skills do usuário
 * POST   /api/skills              → instala skill ({source})
 * DELETE /api/skills/:id          → remove
 * POST   /api/skills/:id/verify   → revalida SKILL.md
 */

import { Hono } from "hono";

const VECTORA_API_URL = process.env.VECTORA_API_URL ?? "http://localhost:8080";

const skills = new Hono();

function headers(cookies?: string): Record<string, string> {
  return {
    "Content-Type": "application/json",
    ...(cookies ? { Cookie: cookies } : {}),
  };
}

skills.get("/", async (c) => {
  try {
    const res = await fetch(`${VECTORA_API_URL}/skills`, {
      headers: headers(c.req.header("Cookie")),
    });
    return c.json(await res.json(), res.status as 200);
  } catch {
    return c.json({ status: "error", message: "Backend indisponível" }, 503);
  }
});

skills.post("/", async (c) => {
  const body = await c.req.json();
  try {
    const res = await fetch(`${VECTORA_API_URL}/skills`, {
      method: "POST",
      headers: headers(c.req.header("Cookie")),
      body: JSON.stringify(body),
    });
    return c.json(await res.json(), res.status as 200);
  } catch {
    return c.json({ status: "error", message: "Backend indisponível" }, 503);
  }
});

skills.delete("/:id", async (c) => {
  try {
    const res = await fetch(
      `${VECTORA_API_URL}/skills/${encodeURIComponent(c.req.param("id"))}`,
      { method: "DELETE", headers: headers(c.req.header("Cookie")) },
    );
    return c.json(await res.json(), res.status as 200);
  } catch {
    return c.json({ status: "error", message: "Backend indisponível" }, 503);
  }
});

skills.post("/:id/verify", async (c) => {
  try {
    const res = await fetch(
      `${VECTORA_API_URL}/skills/${encodeURIComponent(c.req.param("id"))}/verify`,
      { method: "POST", headers: headers(c.req.header("Cookie")) },
    );
    return c.json(await res.json(), res.status as 200);
  } catch {
    return c.json({ ok: false, error: "Backend indisponível" }, 503);
  }
});

export default skills;

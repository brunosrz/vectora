/**
 * Rota de memórias — proxy REST para o MemoryService do Vectora (Bloco N).
 *
 * Todos os endpoints repassam o header Cookie do browser → backend
 * para que o middleware de auth do FastAPI valide o token corretamente.
 */

import { Hono } from "hono";

const VECTORA_API_URL = process.env.VECTORA_API_URL ?? "http://localhost:8080";

const memory = new Hono();

function baseHeaders(cookies?: string): HeadersInit {
  return {
    "Content-Type": "application/json",
    ...(cookies ? { Cookie: cookies } : {}),
  };
}

/** GET /api/memory?limit=50&offset=0 */
memory.get("/", async (c) => {
  const { limit = "50", offset = "0" } = c.req.query();
  const url = `${VECTORA_API_URL}/memory?limit=${limit}&offset=${offset}`;
  try {
    const res = await fetch(url, {
      headers: baseHeaders(c.req.header("Cookie")),
    });
    return c.json(await res.json(), res.status as 200);
  } catch (err) {
    return c.json({ error: String(err) }, 502);
  }
});

/** GET /api/memory/:key */
memory.get("/:key", async (c) => {
  const key = c.req.param("key");
  try {
    const res = await fetch(`${VECTORA_API_URL}/memory/${key}`, {
      headers: baseHeaders(c.req.header("Cookie")),
    });
    return c.json(await res.json(), res.status as 200);
  } catch (err) {
    return c.json({ error: String(err) }, 502);
  }
});

/** PUT /api/memory/:key */
memory.put("/:key", async (c) => {
  const key = c.req.param("key");
  const body = await c.req.json();
  try {
    const res = await fetch(`${VECTORA_API_URL}/memory/${key}`, {
      method: "PUT",
      headers: baseHeaders(c.req.header("Cookie")),
      body: JSON.stringify(body),
    });
    return c.json(await res.json(), res.status as 200);
  } catch (err) {
    return c.json({ error: String(err) }, 502);
  }
});

/** DELETE /api/memory/:key */
memory.delete("/:key", async (c) => {
  const key = c.req.param("key");
  try {
    const res = await fetch(`${VECTORA_API_URL}/memory/${key}`, {
      method: "DELETE",
      headers: baseHeaders(c.req.header("Cookie")),
    });
    return c.json(await res.json(), res.status as 200);
  } catch (err) {
    return c.json({ error: String(err) }, 502);
  }
});

/** DELETE /api/memory (limpa tudo) */
memory.delete("/", async (c) => {
  try {
    const res = await fetch(`${VECTORA_API_URL}/memory`, {
      method: "DELETE",
      headers: baseHeaders(c.req.header("Cookie")),
    });
    return c.json(await res.json(), res.status as 200);
  } catch (err) {
    return c.json({ error: String(err) }, 502);
  }
});

export default memory;

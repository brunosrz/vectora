/**
 * artifacts — proxy para o handler /artifacts do Vectora (Bloco T cont., T8).
 *
 * GET /api/artifacts?session_id=...        → lista artifacts da sessão
 * GET /api/artifacts/:slug?session_id=...  → markdown completo de um artifact
 */

import { Hono } from "hono";

const VECTORA_API_URL = process.env.VECTORA_API_URL ?? "http://localhost:8080";

const artifacts = new Hono();

function cookieHeader(cookies?: string): Record<string, string> {
  return cookies ? { Cookie: cookies } : {};
}

artifacts.get("/", async (c) => {
  const sessionId = c.req.query("session_id") ?? "";
  try {
    const qs = `?session_id=${encodeURIComponent(sessionId)}`;
    const res = await fetch(`${VECTORA_API_URL}/artifacts/${qs}`, {
      headers: cookieHeader(c.req.header("Cookie")),
    });
    const data = await res.json();
    return c.json(data, res.status as 200);
  } catch {
    return c.json({ artifacts: [] }, 503);
  }
});

artifacts.get("/:slug", async (c) => {
  const slug = c.req.param("slug");
  const sessionId = c.req.query("session_id") ?? "";
  try {
    const qs = `?session_id=${encodeURIComponent(sessionId)}`;
    const res = await fetch(
      `${VECTORA_API_URL}/artifacts/${encodeURIComponent(slug)}${qs}`,
      { headers: cookieHeader(c.req.header("Cookie")) },
    );
    const data = await res.json();
    return c.json(data, res.status as 200);
  } catch {
    return c.json({ error: "Backend indisponível" }, 503);
  }
});

export default artifacts;

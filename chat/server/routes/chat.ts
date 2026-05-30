/**
 * Rota de chat — proxy SSE para o backend FastAPI do Vectora.
 *
 * Recebe requisições do browser e as repassa para VECTORA_API_URL,
 * fazendo streaming de volta como SSE. Permite que o frontend use
 * /api/chat/* sem precisar conhecer a URL do servidor Python.
 */

import { Hono } from "hono";
import { stream } from "hono/streaming";

const VECTORA_API_URL = process.env.VECTORA_API_URL ?? "http://localhost:8080";

const chat = new Hono();

/** Proxy de streaming para StreamChat */
chat.post("/stream", async (c) => {
  const body = await c.req.text();

  const upstream = await fetch(
    `${VECTORA_API_URL}/vectora.chat.v1.ChatService/StreamChat`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        // Repassa cookies do browser → backend para validação de auth
        ...(c.req.header("Cookie") ? { Cookie: c.req.header("Cookie")! } : {}),
      },
      body,
    },
  );

  if (!upstream.ok || !upstream.body) {
    return c.json({ error: "Upstream error", status: upstream.status }, 502);
  }

  c.header("Content-Type", "text/event-stream");
  c.header("Cache-Control", "no-cache");
  c.header("X-Accel-Buffering", "no");

  return stream(c, async (s) => {
    const reader = upstream.body!.getReader();
    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        await s.write(value);
      }
    } finally {
      reader.releaseLock();
    }
  });
});

/** Proxy de streaming para ResumeChat (HITL) */
chat.post("/resume", async (c) => {
  const body = await c.req.text();

  const upstream = await fetch(
    `${VECTORA_API_URL}/vectora.chat.v1.ChatService/ResumeChat`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(c.req.header("Cookie") ? { Cookie: c.req.header("Cookie")! } : {}),
      },
      body,
    },
  );

  if (!upstream.ok || !upstream.body) {
    return c.json({ error: "Upstream error", status: upstream.status }, 502);
  }

  c.header("Content-Type", "text/event-stream");
  c.header("Cache-Control", "no-cache");
  c.header("X-Accel-Buffering", "no");

  return stream(c, async (s) => {
    const reader = upstream.body!.getReader();
    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        await s.write(value);
      }
    } finally {
      reader.releaseLock();
    }
  });
});

/** Proxy para GetTools (autodescoberta de schema) */
chat.get("/tools", async (c) => {
  const upstream = await fetch(
    `${VECTORA_API_URL}/vectora.chat.v1.ChatService/GetTools`,
  );
  if (!upstream.ok) {
    return c.json({ tools: [] });
  }
  return c.json(await upstream.json());
});

export default chat;

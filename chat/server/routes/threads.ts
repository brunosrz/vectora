/**
 * Rota de threads — proxy REST para o ThreadService do Vectora.
 *
 * Todos os endpoints repassam o header Cookie do browser → backend
 * para que o middleware de auth do FastAPI valide o token corretamente.
 */

import { Hono } from "hono";

const VECTORA_API_URL = process.env.VECTORA_API_URL ?? "http://localhost:8080";

const threads = new Hono();

async function proxyPost(path: string, body: unknown, cookies?: string) {
  const res = await fetch(`${VECTORA_API_URL}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      // Repassa cookies do browser → backend para validação de auth
      ...(cookies ? { Cookie: cookies } : {}),
    },
    body: JSON.stringify(body),
  });
  return res;
}

threads.post("/create", async (c) => {
  const res = await proxyPost(
    "/vectora.chat.v1.ThreadService/CreateThread",
    {},
    c.req.header("Cookie"),
  );
  return c.json(await res.json(), res.status as 200);
});

threads.post("/get", async (c) => {
  const body = await c.req.json();
  const res = await proxyPost(
    "/vectora.chat.v1.ThreadService/GetThread",
    body,
    c.req.header("Cookie"),
  );
  return c.json(await res.json(), res.status as 200);
});

threads.post("/list", async (c) => {
  const body = await c.req.json().catch(() => ({}));
  const res = await proxyPost(
    "/vectora.chat.v1.ThreadService/ListThreads",
    body,
    c.req.header("Cookie"),
  );
  return c.json(await res.json(), res.status as 200);
});

threads.post("/delete", async (c) => {
  const body = await c.req.json();
  const res = await proxyPost(
    "/vectora.chat.v1.ThreadService/DeleteThread",
    body,
    c.req.header("Cookie"),
  );
  return c.json(await res.json(), res.status as 200);
});

threads.post("/update", async (c) => {
  const body = await c.req.json();
  const res = await proxyPost(
    "/vectora.chat.v1.ThreadService/UpdateThread",
    body,
    c.req.header("Cookie"),
  );
  return c.json(await res.json(), res.status as 200);
});

threads.post("/history", async (c) => {
  const body = await c.req.json();
  const res = await proxyPost(
    "/vectora.chat.v1.ThreadService/GetHistory",
    body,
    c.req.header("Cookie"),
  );
  return c.json(await res.json(), res.status as 200);
});

export default threads;

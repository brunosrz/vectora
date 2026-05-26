/**
 * Rota de threads — proxy REST para o ThreadService do Vectora.
 */

import { Hono } from "hono";

const VECTORA_API_URL = process.env.VECTORA_API_URL ?? "http://localhost:8080";

const threads = new Hono();

async function proxyPost(path: string, body: unknown) {
  const res = await fetch(`${VECTORA_API_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return res;
}

threads.post("/create", async (c) => {
  const res = await proxyPost(
    "/vectora.chat.v1.ThreadService/CreateThread",
    {},
  );
  return c.json(await res.json(), res.status as 200);
});

threads.post("/get", async (c) => {
  const body = await c.req.json();
  const res = await proxyPost("/vectora.chat.v1.ThreadService/GetThread", body);
  return c.json(await res.json(), res.status as 200);
});

threads.post("/list", async (c) => {
  const body = await c.req.json().catch(() => ({}));
  const res = await proxyPost(
    "/vectora.chat.v1.ThreadService/ListThreads",
    body,
  );
  return c.json(await res.json(), res.status as 200);
});

threads.post("/delete", async (c) => {
  const body = await c.req.json();
  const res = await proxyPost(
    "/vectora.chat.v1.ThreadService/DeleteThread",
    body,
  );
  return c.json(await res.json(), res.status as 200);
});

threads.post("/history", async (c) => {
  const body = await c.req.json();
  const res = await proxyPost(
    "/vectora.chat.v1.ThreadService/GetHistory",
    body,
  );
  return c.json(await res.json(), res.status as 200);
});

export default threads;

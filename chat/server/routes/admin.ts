/**
 * Rota de administração — proxy REST para o handler admin do Vectora (Bloco P).
 *
 * Todos os endpoints repassa cookies do browser → backend para auth.
 */

import { Hono } from "hono";

const VECTORA_API_URL = process.env.VECTORA_API_URL ?? "http://localhost:8080";

const admin = new Hono();

function baseHeaders(cookies?: string): HeadersInit {
  return {
    "Content-Type": "application/json",
    ...(cookies ? { Cookie: cookies } : {}),
  };
}

admin.get("/users", async (c) => {
  const res = await fetch(`${VECTORA_API_URL}/admin/users`, {
    headers: baseHeaders(c.req.header("Cookie")),
  });
  return c.json(await res.json(), res.status as 200);
});

admin.get("/users/:id", async (c) => {
  const res = await fetch(
    `${VECTORA_API_URL}/admin/users/${c.req.param("id")}`,
    {
      headers: baseHeaders(c.req.header("Cookie")),
    },
  );
  return c.json(await res.json(), res.status as 200);
});

admin.patch("/users/:id/role", async (c) => {
  const body = await c.req.json();
  const res = await fetch(
    `${VECTORA_API_URL}/admin/users/${c.req.param("id")}/role`,
    {
      method: "PATCH",
      headers: baseHeaders(c.req.header("Cookie")),
      body: JSON.stringify(body),
    },
  );
  return c.json(await res.json(), res.status as 200);
});

admin.delete("/users/:id", async (c) => {
  const res = await fetch(
    `${VECTORA_API_URL}/admin/users/${c.req.param("id")}`,
    {
      method: "DELETE",
      headers: baseHeaders(c.req.header("Cookie")),
    },
  );
  return c.json(await res.json(), res.status as 200);
});

admin.get("/tools", async (c) => {
  const res = await fetch(`${VECTORA_API_URL}/admin/tools`, {
    headers: baseHeaders(c.req.header("Cookie")),
  });
  return c.json(await res.json(), res.status as 200);
});

admin.post("/tools/:name/toggle", async (c) => {
  const body = await c.req.json();
  const res = await fetch(
    `${VECTORA_API_URL}/admin/tools/${c.req.param("name")}/toggle`,
    {
      method: "POST",
      headers: baseHeaders(c.req.header("Cookie")),
      body: JSON.stringify(body),
    },
  );
  return c.json(await res.json(), res.status as 200);
});

admin.get("/system", async (c) => {
  const res = await fetch(`${VECTORA_API_URL}/admin/system`, {
    headers: baseHeaders(c.req.header("Cookie")),
  });
  return c.json(await res.json(), res.status as 200);
});

admin.get("/config", async (c) => {
  const res = await fetch(`${VECTORA_API_URL}/admin/config`, {
    headers: baseHeaders(c.req.header("Cookie")),
  });
  return c.json(await res.json(), res.status as 200);
});

admin.patch("/config", async (c) => {
  const body = await c.req.json();
  const res = await fetch(`${VECTORA_API_URL}/admin/config`, {
    method: "PATCH",
    headers: baseHeaders(c.req.header("Cookie")),
    body: JSON.stringify(body),
  });
  return c.json(await res.json(), res.status as 200);
});

export default admin;

/**
 * Rota de auth — proxy REST para o AuthService do Vectora.
 *
 * Repassa cookies httpOnly entre browser ↔ Next.js ↔ FastAPI,
 * garantindo que os tokens nunca fiquem expostos ao JavaScript do cliente.
 */

import { Hono } from "hono";

const VECTORA_API_URL = process.env.VECTORA_API_URL ?? "http://localhost:8080";

const auth = new Hono();

/** Proxy genérico que repassa headers de cookie em ambas as direções. */
async function proxyAuth(
  path: string,
  method: "GET" | "POST" | "DELETE" | "PATCH",
  body: unknown | null,
  incomingCookies: string,
) {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (incomingCookies) {
    headers["Cookie"] = incomingCookies;
  }

  const res = await fetch(`${VECTORA_API_URL}${path}`, {
    method,
    headers,
    body: body !== null ? JSON.stringify(body) : undefined,
  });

  return res;
}

/** Copia os Set-Cookie do upstream para a resposta Hono. */
function copySetCookie(res: Response, c: any) {
  const setCookie = res.headers.getSetCookie?.() ?? [];
  for (const cookie of setCookie) {
    c.header("Set-Cookie", cookie, { append: true });
  }
}

auth.get("/has-users", async (c) => {
  const res = await proxyAuth("/auth/has-users", "GET", null, "");
  return c.json(await res.json(), res.status as 200);
});

auth.get("/invite/:token", async (c) => {
  const token = c.req.param("token");
  const res = await proxyAuth(`/auth/invite/${token}`, "GET", null, "");
  return c.json(await res.json(), res.status as 200);
});

auth.post("/signup", async (c) => {
  const body = await c.req.json();
  const res = await proxyAuth(
    "/auth/signup",
    "POST",
    body,
    c.req.header("Cookie") ?? "",
  );
  copySetCookie(res, c);
  return c.json(await res.json(), res.status as 200);
});

auth.post("/signin", async (c) => {
  const body = await c.req.json();
  const res = await proxyAuth(
    "/auth/signin",
    "POST",
    body,
    c.req.header("Cookie") ?? "",
  );
  copySetCookie(res, c);
  return c.json(await res.json(), res.status as 200);
});

auth.post("/refresh", async (c) => {
  const body = await c.req.json().catch(() => ({}));
  const res = await proxyAuth(
    "/auth/refresh",
    "POST",
    body,
    c.req.header("Cookie") ?? "",
  );
  copySetCookie(res, c);
  return c.json(await res.json(), res.status as 200);
});

auth.post("/signout", async (c) => {
  const body = await c.req.json().catch(() => ({}));
  const res = await proxyAuth(
    "/auth/signout",
    "POST",
    body,
    c.req.header("Cookie") ?? "",
  );
  copySetCookie(res, c);
  return c.json(await res.json(), res.status as 200);
});

auth.get("/me", async (c) => {
  const res = await proxyAuth(
    "/auth/me",
    "GET",
    null,
    c.req.header("Cookie") ?? "",
  );
  return c.json(await res.json(), res.status as 200);
});

auth.patch("/me", async (c) => {
  const body = await c.req.json().catch(() => ({}));
  const res = await proxyAuth(
    "/auth/me",
    "PATCH",
    body,
    c.req.header("Cookie") ?? "",
  );
  return c.json(await res.json(), res.status as 200);
});

auth.get("/ws-token", async (c) => {
  const res = await proxyAuth(
    "/auth/ws-token",
    "GET",
    null,
    c.req.header("Cookie") ?? "",
  );
  return c.json(await res.json(), res.status as 200);
});

auth.get("/usage", async (c) => {
  const res = await proxyAuth(
    "/auth/usage",
    "GET",
    null,
    c.req.header("Cookie") ?? "",
  );
  return c.json(await res.json(), res.status as 200);
});

// G.2.4 — chaves SSH por usuário (workspaces remotos)
auth.get("/ssh-keys", async (c) => {
  const res = await proxyAuth(
    "/auth/ssh-keys",
    "GET",
    null,
    c.req.header("Cookie") ?? "",
  );
  return c.json(await res.json(), res.status as 200);
});

auth.post("/ssh-keys", async (c) => {
  // Multipart precisa repassar o body cru — o proxyAuth genérico
  // assume JSON. Usamos fetch direto preservando headers e body.
  const VECTORA_API_URL =
    process.env.VECTORA_API_URL ?? "http://localhost:8080";
  const cookies = c.req.header("Cookie") ?? "";
  const contentType = c.req.header("Content-Type") ?? "";
  const arrayBuf = await c.req.arrayBuffer();
  const res = await fetch(`${VECTORA_API_URL}/auth/ssh-keys`, {
    method: "POST",
    headers: {
      ...(cookies ? { Cookie: cookies } : {}),
      ...(contentType ? { "Content-Type": contentType } : {}),
    },
    body: arrayBuf,
  });
  return c.json(await res.json(), res.status as 200);
});

auth.delete("/ssh-keys/:id", async (c) => {
  const res = await proxyAuth(
    `/auth/ssh-keys/${c.req.param("id")}`,
    "DELETE",
    null,
    c.req.header("Cookie") ?? "",
  );
  return c.json(await res.json(), res.status as 200);
});

auth.post("/change-password", async (c) => {
  const body = await c.req.json();
  const res = await proxyAuth(
    "/auth/change-password",
    "POST",
    body,
    c.req.header("Cookie") ?? "",
  );
  copySetCookie(res, c);
  return c.json(await res.json(), res.status as 200);
});

auth.get("/envs", async (c) => {
  const res = await proxyAuth(
    "/auth/envs",
    "GET",
    null,
    c.req.header("Cookie") ?? "",
  );
  return c.json(await res.json(), res.status as 200);
});

auth.post("/envs", async (c) => {
  const body = await c.req.json();
  const res = await proxyAuth(
    "/auth/envs",
    "POST",
    body,
    c.req.header("Cookie") ?? "",
  );
  return c.json(await res.json(), res.status as 200);
});

auth.delete("/envs/:key", async (c) => {
  const key = c.req.param("key");
  const res = await proxyAuth(
    `/auth/envs/${key}`,
    "DELETE",
    null,
    c.req.header("Cookie") ?? "",
  );
  return c.json(await res.json(), res.status as 200);
});

auth.get("/users", async (c) => {
  const res = await proxyAuth(
    "/auth/users",
    "GET",
    null,
    c.req.header("Cookie") ?? "",
  );
  return c.json(await res.json(), res.status as 200);
});

auth.get("/audit", async (c) => {
  const res = await proxyAuth(
    "/auth/audit",
    "GET",
    null,
    c.req.header("Cookie") ?? "",
  );
  return c.json(await res.json(), res.status as 200);
});

export default auth;

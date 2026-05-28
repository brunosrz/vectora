/**
 * Rota de workspaces — proxy REST para o WorkspaceService do Vectora (G1).
 *
 * GET  /api/workspaces         → lista todos os workspaces
 * GET  /api/workspaces/active  → workspace ativo (cwd atual do servidor)
 * POST /api/workspaces/set-active → troca o workspace ativo
 */

import { Hono } from "hono";

const VECTORA_API_URL = process.env.VECTORA_API_URL ?? "http://localhost:8080";

const workspaces = new Hono();

// ─── helpers ─────────────────────────────────────────────────────────────────

function backendUrl(path: string) {
  return `${VECTORA_API_URL}${path}`;
}

function cookieHeader(cookies?: string): Record<string, string> {
  return cookies ? { Cookie: cookies } : {};
}

// ─── rotas ───────────────────────────────────────────────────────────────────

workspaces.get("/", async (c) => {
  try {
    const res = await fetch(backendUrl("/vectora.workspace.v1.WorkspaceService/ListWorkspaces"), {
      headers: {
        ...cookieHeader(c.req.header("Cookie")),
      },
    });
    const data = await res.json();
    return c.json(data, res.status as 200);
  } catch {
    return c.json({ status: "error", message: "Backend indisponível" }, 503);
  }
});

workspaces.get("/active", async (c) => {
  try {
    const res = await fetch(backendUrl("/vectora.workspace.v1.WorkspaceService/GetActiveWorkspace"), {
      headers: cookieHeader(c.req.header("Cookie")),
    });
    const data = await res.json();
    return c.json(data, res.status as 200);
  } catch {
    return c.json({ status: "error", message: "Backend indisponível" }, 503);
  }
});

workspaces.post("/set-active", async (c) => {
  const body = await c.req.json();
  try {
    const res = await fetch(backendUrl("/vectora.workspace.v1.WorkspaceService/SetActiveWorkspace"), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...cookieHeader(c.req.header("Cookie")),
      },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    return c.json(data, res.status as 200);
  } catch {
    return c.json({ status: "error", message: "Backend indisponível" }, 503);
  }
});

export default workspaces;

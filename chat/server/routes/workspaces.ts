/**
 * Rota de workspaces — proxy REST para o WorkspaceService do Vectora.
 *
 * GET  /api/workspaces           → lista todos os workspaces
 * GET  /api/workspaces/active    → workspace ativo
 * POST /api/workspaces/set-active → troca o workspace ativo
 * POST /api/workspaces/create    → registra pasta como workspace
 * POST /api/workspaces/trust     → marca workspace como confiável
 * POST /api/workspaces/git-init  → roda git init na pasta do workspace
 * GET  /api/workspaces/browse    → lista subpastas de um caminho
 * GET  /api/workspaces/worktrees → lista worktrees de um workspace
 * POST /api/workspaces/worktrees → cria worktree
 */

import { Hono } from "hono";

const VECTORA_API_URL = process.env.VECTORA_API_URL ?? "http://localhost:8080";
const SERVICE = "/vectora.workspace.v1.WorkspaceService";

const workspaces = new Hono();

// ─── helpers ─────────────────────────────────────────────────────────────────

function cookieHeader(cookies?: string): Record<string, string> {
  return cookies ? { Cookie: cookies } : {};
}

async function proxyGet(c: any, method: string, search = "") {
  try {
    const res = await fetch(`${VECTORA_API_URL}${SERVICE}/${method}${search}`, {
      headers: cookieHeader(c.req.header("Cookie")),
    });
    const data = await res.json();
    return c.json(data, res.status as 200);
  } catch {
    return c.json({ status: "error", message: "Backend indisponível" }, 503);
  }
}

async function proxyPost(c: any, method: string, body: unknown) {
  try {
    const res = await fetch(`${VECTORA_API_URL}${SERVICE}/${method}`, {
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
}

// ─── rotas ───────────────────────────────────────────────────────────────────

workspaces.get("/", (c) => proxyGet(c, "ListWorkspaces"));

workspaces.get("/active", (c) => proxyGet(c, "GetActiveWorkspace"));

workspaces.post("/set-active", async (c) =>
  proxyPost(c, "SetActiveWorkspace", await c.req.json()),
);

workspaces.post("/create", async (c) =>
  proxyPost(c, "CreateWorkspace", await c.req.json()),
);

workspaces.post("/trust", async (c) =>
  proxyPost(c, "TrustWorkspace", await c.req.json()),
);

workspaces.post("/git-init", async (c) =>
  proxyPost(c, "GitInitWorkspace", await c.req.json()),
);

workspaces.get("/browse", (c) => {
  const path = c.req.query("path") ?? "";
  return proxyGet(c, "BrowseDir", `?path=${encodeURIComponent(path)}`);
});

workspaces.get("/safe-roots", (c) => proxyGet(c, "ListSafeRoots"));

// G.2.6 — workspaces remotos
workspaces.get("/codespaces", (c) => proxyGet(c, "Codespaces"));
workspaces.post("/test-ssh", async (c) =>
  proxyPost(c, "TestSsh", await c.req.json()),
);
workspaces.post("/create-remote", async (c) =>
  proxyPost(c, "CreateRemoteWorkspace", await c.req.json()),
);

workspaces.get("/worktrees", (c) => {
  const id = c.req.query("workspace_id") ?? "";
  return proxyGet(
    c,
    "ListWorktrees",
    `?workspace_id=${encodeURIComponent(id)}`,
  );
});

workspaces.post("/worktrees", async (c) =>
  proxyPost(c, "CreateWorktree", await c.req.json()),
);

// ─── Workbench views (T6/T7) ────────────────────────────────────────────────
// Estes endpoints REST batem direto no router REST `/workspaces/{id}/...`,
// sem passar pelo prefix Connect-style usado nas rotas acima.

async function proxyView(c: any, path: string, search = "") {
  try {
    const res = await fetch(`${VECTORA_API_URL}/workspaces${path}${search}`, {
      headers: cookieHeader(c.req.header("Cookie")),
    });
    const data = await res.json();
    return c.json(data, res.status as 200);
  } catch {
    return c.json({ error: "Backend indisponível" }, 503);
  }
}

workspaces.get("/:id/tree", (c) => {
  const id = c.req.param("id");
  const path = c.req.query("path") ?? "";
  return proxyView(c, `/${id}/tree`, `?path=${encodeURIComponent(path)}`);
});

workspaces.get("/:id/file", (c) => {
  const id = c.req.param("id");
  const path = c.req.query("path") ?? "";
  return proxyView(c, `/${id}/file`, `?path=${encodeURIComponent(path)}`);
});

workspaces.get("/:id/git/diff", (c) => {
  const id = c.req.param("id");
  return proxyView(c, `/${id}/git/diff`);
});

workspaces.get("/:id/git/diff/file", (c) => {
  const id = c.req.param("id");
  const path = c.req.query("path") ?? "";
  return proxyView(
    c,
    `/${id}/git/diff/file`,
    `?path=${encodeURIComponent(path)}`,
  );
});

export default workspaces;

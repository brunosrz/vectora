/**
 * Hono app factory — montado como catch-all handler do Next.js App Router.
 *
 * Centraliza todas as rotas de API em /api/* no mesmo processo do Next.js,
 * sem servidor separado e sem CORS. O cliente SSE do browser aponta para
 * /api/chat/stream em vez de http://localhost:8080 diretamente.
 */

import { Hono } from "hono";
import authRoutes from "./routes/auth";
import chatRoutes from "./routes/chat";
import healthRoutes from "./routes/health";
import threadRoutes from "./routes/threads";
import workspacesRoutes from "./routes/workspaces";

const app = new Hono().basePath("/api");

app.route("/auth", authRoutes);
app.route("/chat", chatRoutes);
app.route("/threads", threadRoutes);
app.route("/health", healthRoutes);
app.route("/workspaces", workspacesRoutes);

// Métricas: proxy para o endpoint /metrics do FastAPI
app.get("/metrics", async (c) => {
  const VECTORA_API_URL =
    process.env.VECTORA_API_URL ?? "http://localhost:8080";
  try {
    const res = await fetch(`${VECTORA_API_URL}/metrics`);
    if (!res.ok) return c.json({ spans: [] });
    return c.json(await res.json());
  } catch {
    return c.json({ spans: [] });
  }
});

export default app;

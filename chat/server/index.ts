/**
 * Hono app factory — montado como catch-all handler do Next.js App Router.
 *
 * Centraliza todas as rotas de API em /api/* no mesmo processo do Next.js,
 * sem servidor separado e sem CORS. O cliente SSE do browser aponta para
 * /api/chat/stream em vez de http://localhost:8080 diretamente.
 */

import { Hono } from "hono";
import adminRoutes from "./routes/admin";
import artifactsRoutes from "./routes/artifacts";
import authRoutes from "./routes/auth";
import chatRoutes from "./routes/chat";
import healthRoutes from "./routes/health";
import integrationsRoutes from "./routes/integrations";
import licenseRoutes from "./routes/license";
import memoryRoutes from "./routes/memory";
import pluginsRoutes from "./routes/plugins";
import skillsRoutes from "./routes/skills";
import threadRoutes from "./routes/threads";
import toolsRoutes from "./routes/tools";
import updatesRoutes from "./routes/updates";
import workspacesRoutes from "./routes/workspaces";

const app = new Hono().basePath("/api");

// Erros de rede (ECONNREFUSED) em qualquer rota retornam 503 JSON
// em vez de um 500 HTML que quebra clientes que esperam JSON.
app.onError((err, c) => {
  const isNetworkError =
    err instanceof TypeError &&
    (err.message.includes("fetch failed") ||
      err.message.includes("ECONNREFUSED"));
  if (isNetworkError) {
    return c.json(
      { error: "backend_unavailable", detail: "Vectora backend offline" },
      503,
    );
  }
  console.error("[vectora] unhandled route error:", err);
  return c.json({ error: "internal_error" }, 500);
});

app.route("/auth", authRoutes);
app.route("/chat", chatRoutes);
app.route("/threads", threadRoutes);
app.route("/health", healthRoutes);
app.route("/memory", memoryRoutes);
app.route("/integrations", integrationsRoutes);
app.route("/admin", adminRoutes);
app.route("/workspaces", workspacesRoutes);
app.route("/plugins", pluginsRoutes);
app.route("/skills", skillsRoutes);
app.route("/license", licenseRoutes);
app.route("/updates", updatesRoutes);
app.route("/tools", toolsRoutes);
app.route("/artifacts", artifactsRoutes);

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

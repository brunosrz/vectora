/**
 * registry/ (Fase F) — "um registry, três catálogos"
 * (documents/extensibility-roadmap.md §5): mcp, skills e extensions são
 * recursos irmãos do mesmo Worker, não três serviços diferentes.
 *
 * `mcp` e `skills` são catálogos reais em D1 (`mcp_catalog`/`skills_catalog`,
 * `migrations/0001_schema.sql`) — curadoria hoje é só via PR editando o seed
 * dessa migration (não há submissão pública ainda, ver roadmap §3.5). O
 * cliente Vectora (`backend/services/registry_client.py`) já sabe cair pro
 * fallback local/hardcoded quando o registry remoto está vazio ou fora do
 * ar — lista vazia aqui é um estado válido, não erro.
 *
 * `extensions` continua placeholder — depende do SDK de autoria
 * (`vectora_ext` Python, `@vectora/extension-sdk` TS) e do Extension Host,
 * nenhum dos dois existe ainda (fora de escopo, roadmap §2).
 */
import { Hono } from "hono";
import type { Env } from "../gateway/types";

export const registry = new Hono<{ Bindings: Env }>();

registry.get("/mcp", async (c) => {
  const { results } = await c.env.DB.prepare(
    "SELECT id, name, description, install_cmd, env_vars, homepage, category, vectora_verified, downloads_count, updated_at FROM mcp_catalog ORDER BY downloads_count DESC",
  ).all();
  return c.json({ entries: results ?? [] });
});

registry.get("/skills", async (c) => {
  const { results } = await c.env.DB.prepare(
    "SELECT id, name, description, source, tags, vectora_verified, downloads_count, updated_at FROM skills_catalog ORDER BY downloads_count DESC",
  ).all();
  return c.json({ entries: results ?? [] });
});

registry.get("/extensions", (c) => c.json({ entries: [] }));

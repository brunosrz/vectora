/**
 * rag-library/ (Fase E) — catálogo de bancos RAG pré-indexados públicos.
 *
 * Escopo mínimo: lista + redirect pro storage externo (fora da Cloudflare —
 * decisão do usuário, ver plano). Não reindexação, não upload de terceiros
 * nesta fase. `rag_packages` é só metadado de leitura em D1; o binário em si
 * vive no provedor de storage escolhido (Backblaze B2 recomendado — decisão
 * em aberto, ver "Decisões em aberto" do plano).
 */
import { Hono } from "hono";
import type { Env } from "../relay/types";

export const ragLibrary = new Hono<{ Bindings: Env }>();

interface RagPackageRow {
  id: string;
  name: string;
  source_lib: string;
  source_version: string;
  size_bytes: number;
  checksum: string;
  storage_url: string;
  updated_at: string;
}

ragLibrary.get("/", async (c) => {
  const { results } = await c.env.DB.prepare(
    "SELECT id, name, source_lib, source_version, size_bytes, checksum, updated_at FROM rag_packages ORDER BY name",
  ).all();
  return c.json(results);
});

ragLibrary.get("/:id/download", async (c) => {
  const id = c.req.param("id");
  const row = await c.env.DB.prepare(
    "SELECT storage_url FROM rag_packages WHERE id = ?",
  )
    .bind(id)
    .first<Pick<RagPackageRow, "storage_url">>();
  if (!row) return c.json({ error: "not_found" }, 404);

  return c.redirect(row.storage_url, 302);
});

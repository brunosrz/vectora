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
import { enqueueJob } from "../lib/queue";

export const ragLibrary = new Hono<{ Bindings: Env }>();

/**
 * Motivo fixo de falha do reindex — não existe provedor de storage externo
 * configurado ainda (decisão em aberto, ver documents/plan.md Bloco K e o
 * histórico de decisões da Fase E). Marcar como "failed" com esse motivo é
 * o comportamento honesto pro estado atual da infra: o job roda de verdade,
 * só não tem onde baixar/indexar nada ainda.
 */
export const NO_STORAGE_PROVIDER_REASON =
  "Provedor de storage externo ainda não configurado";

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

/**
 * Dispara a reindexação de um pacote existente. Marca `status='pending'`
 * na hora (síncrono) e enfileira o job de verdade — o consumer é quem
 * decide o resultado (hoje sempre `failed`, ver NO_STORAGE_PROVIDER_REASON).
 */
ragLibrary.post("/:id/reindex", async (c) => {
  const id = c.req.param("id");
  const row = await c.env.DB.prepare("SELECT id FROM rag_packages WHERE id = ?")
    .bind(id)
    .first();
  if (!row) return c.json({ error: "not_found" }, 404);

  await c.env.DB.prepare(
    "UPDATE rag_packages SET status = 'pending', status_reason = NULL WHERE id = ?",
  )
    .bind(id)
    .run();

  await enqueueJob(c.env, { type: "rag_reindex", packageId: id });

  return c.json({ ok: true, status: "pending" });
});

/** Chamado pelo consumer da fila `vectora-jobs` (job `rag_reindex`). */
export async function processRagReindex(
  env: Env,
  packageId: string,
): Promise<void> {
  await env.DB.prepare(
    "UPDATE rag_packages SET status = 'failed', status_reason = ? WHERE id = ?",
  )
    .bind(NO_STORAGE_PROVIDER_REASON, packageId)
    .run();
}

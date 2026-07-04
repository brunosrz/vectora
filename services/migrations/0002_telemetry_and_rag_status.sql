-- Tabela de telemetria genérica (crash/uso) enviada pelo backend Python do
-- Vectora local — POST /telemetry/ingest, sempre via fila (vectora-jobs,
-- job telemetry_ingest), nunca gravada direto na rota HTTP.
CREATE TABLE telemetry_events (
  id          TEXT PRIMARY KEY,
  source      TEXT NOT NULL,    -- 'vectora-app' | 'vectora-desktop'
  event_type  TEXT NOT NULL,
  payload     TEXT NOT NULL,    -- JSON serializado
  received_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX telemetry_events_source_idx ON telemetry_events(source, event_type);

-- Estado de indexação da RAG library. Pacotes existentes (nenhum ainda,
-- catálogo vazio hoje) nascem 'ready' — só quem passa por /reindex entra
-- em 'pending'/'failed'.
ALTER TABLE rag_packages ADD COLUMN status TEXT NOT NULL DEFAULT 'ready'
  CHECK (status IN ('ready', 'pending', 'failed'));
ALTER TABLE rag_packages ADD COLUMN status_reason TEXT;

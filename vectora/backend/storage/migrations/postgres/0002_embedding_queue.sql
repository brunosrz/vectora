-- Migration 0002: fila de embedding assíncrono (PostgreSQL)
-- Usada pelo PostgresQueueDB em STORAGE_MODE=complete.

-- up
CREATE TABLE IF NOT EXISTS vectora_embedding_queue (
    id           BIGSERIAL    PRIMARY KEY,
    queue_id     TEXT         NOT NULL UNIQUE,
    task_json    JSONB        NOT NULL,
    status       TEXT         NOT NULL DEFAULT 'pending',
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT now(),
    processed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_veq_status ON vectora_embedding_queue(status);

-- down
DROP INDEX  IF EXISTS ix_veq_status;
DROP TABLE  IF EXISTS vectora_embedding_queue;

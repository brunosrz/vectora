-- Migration 0005: tabela de fila de embedding (PostgreSQL — modo complete)
-- Criada sob demanda pelo PostgresQueueDB quando em STORAGE_MODE=complete.
-- Armazena tarefas de embedding assíncrono com suporte a retry e DLQ.

-- up
CREATE TABLE IF NOT EXISTS vectora_embedding_queue (
    id           BIGSERIAL    PRIMARY KEY,
    queue_id     TEXT         NOT NULL UNIQUE,
    task_json    JSONB        NOT NULL,
    status       TEXT         NOT NULL DEFAULT 'pending',
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT now(),
    processed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_veq_status
    ON vectora_embedding_queue (status);

-- down
DROP TABLE IF EXISTS vectora_embedding_queue;

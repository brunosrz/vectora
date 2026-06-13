-- Migration 0003: tabela de spans de observabilidade
-- Extrai CREATE TABLE de src/services/tracer.py (_SCHEMA)

-- up
CREATE TABLE IF NOT EXISTS spans (
    span_id      TEXT PRIMARY KEY,
    parent_id    TEXT,
    session_id   INTEGER,
    node         TEXT NOT NULL,
    event        TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'ok',
    started_at   TEXT NOT NULL,
    ended_at     TEXT,
    duration_ms  REAL,
    in_tokens    INTEGER,
    out_tokens   INTEGER,
    metadata     TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_spans_session ON spans(session_id);
CREATE INDEX IF NOT EXISTS idx_spans_node    ON spans(node);
CREATE INDEX IF NOT EXISTS idx_spans_started ON spans(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_spans_parent  ON spans(parent_id);

-- down
DROP TABLE IF EXISTS spans;

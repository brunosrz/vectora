-- Migration 0001: schema base de sessões, artifacts e compartilhamento (PostgreSQL)
-- Usa tipos nativos Postgres: TIMESTAMPTZ, JSONB, BIGINT.

-- up
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS vectora_sessions (
    thread_id     TEXT         PRIMARY KEY,
    user_type     TEXT         NOT NULL DEFAULT 'human',
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
    last_activity TIMESTAMPTZ  NOT NULL DEFAULT now(),
    message_count BIGINT       NOT NULL DEFAULT 0,
    extra         JSONB        NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS vectora_checkpoint_artifacts (
    id              TEXT         PRIMARY KEY,
    thread_id       TEXT         NOT NULL,
    checkpoint_id   TEXT         NOT NULL,
    strategy        TEXT         NOT NULL DEFAULT 'git',
    git_sha         TEXT,
    snapshot_path   TEXT,
    files_touched   JSONB        NOT NULL DEFAULT '[]',
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS shared_threads (
    token       TEXT         PRIMARY KEY,
    thread_id   TEXT         NOT NULL,
    created_by  TEXT         NOT NULL DEFAULT '',
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    expires_at  TIMESTAMPTZ  NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sessions_activity ON vectora_sessions(last_activity DESC);
CREATE INDEX IF NOT EXISTS idx_artifacts_thread  ON vectora_checkpoint_artifacts(thread_id);
CREATE INDEX IF NOT EXISTS idx_shares_thread     ON shared_threads(thread_id);
CREATE INDEX IF NOT EXISTS idx_shares_expires    ON shared_threads(expires_at);

-- down
DROP TABLE IF EXISTS shared_threads;
DROP TABLE IF EXISTS vectora_checkpoint_artifacts;
DROP TABLE IF EXISTS vectora_sessions;

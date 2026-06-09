-- Migration 0001: tabelas de autenticação e auditoria
-- Extrai CREATE TABLE de src/services/auth.py (_ensure_schema)
-- Compatible com checkpoints.db e vectora.db

-- up
CREATE TABLE IF NOT EXISTS users (
    id                 TEXT PRIMARY KEY,
    email              TEXT NOT NULL UNIQUE,
    password_hash      TEXT NOT NULL,
    role               TEXT NOT NULL DEFAULT 'member',
    name               TEXT NOT NULL DEFAULT '',
    env_overrides_json TEXT NOT NULL DEFAULT '{}',
    created_at         TEXT NOT NULL,
    last_login_at      TEXT
);

CREATE TABLE IF NOT EXISTS refresh_tokens (
    token_hash  TEXT    PRIMARY KEY,
    user_id     TEXT    NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at  TEXT    NOT NULL,
    revoked     INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS audit (
    id            TEXT    PRIMARY KEY,
    user_id       TEXT,
    action        TEXT    NOT NULL,
    target_type   TEXT,
    target_id     TEXT,
    timestamp     TEXT    NOT NULL,
    ip            TEXT,
    user_agent    TEXT,
    success       INTEGER NOT NULL DEFAULT 1,
    metadata_json TEXT    NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS invites (
    token_hash  TEXT    PRIMARY KEY,
    email       TEXT,
    role        TEXT    NOT NULL DEFAULT 'member',
    created_by  TEXT,
    expires_at  TEXT    NOT NULL,
    used_at     TEXT,
    created_at  TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_users_email         ON users(email);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user ON refresh_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_user          ON audit(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp     ON audit(timestamp DESC);

-- down
DROP TABLE IF EXISTS invites;
DROP TABLE IF EXISTS audit;
DROP TABLE IF EXISTS refresh_tokens;
DROP TABLE IF EXISTS users;

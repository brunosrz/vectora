-- Migration 0009: identidade por username (Sprint G)
-- Espelha o ALTER idempotente de backend/rbac/auth.py::_ensure_schema — a
-- fonte de verdade de auth é sempre o SQLite (~/.vectora/checkpoints.db). O
-- índice único é parcial (ignora ''); todo usuário passa a ter username
-- preenchido pelo backfill do _ensure_schema.

-- up
ALTER TABLE users ADD COLUMN username TEXT NOT NULL DEFAULT '';
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username ON users(username) WHERE username != '';

-- down
DROP INDEX IF EXISTS idx_users_username;
ALTER TABLE users DROP COLUMN username;

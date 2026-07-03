-- Schema D1 do vectora-services — substitui o Postgres do Supabase.
--
-- Sem RLS (D1/SQLite não tem) — autorização é responsabilidade de cada
-- handler (checar user_id da sessão contra o dono da linha antes de
-- retornar/mutar), mesmo princípio já vinculante do CLAUDE.md regra 7
-- ("Auth-first para tudo server").
--
-- Espelha o shape das tabelas Supabase (company/supabase/migrations/*.sql),
-- com dois ajustes de fundo:
--   1. `users` substitui auth.users + profiles combinados (D1 não tem um
--      sistema de auth embutido separado — o próprio services é o auth).
--   2. `sessions` é novo — token opaco de sessão (não existia no Supabase,
--      que gerenciava isso internamente via JWT). Ver src/auth/session.ts.

CREATE TABLE users (
  id             TEXT PRIMARY KEY,  -- uuid gerado em auth/routes.ts
  email          TEXT NOT NULL UNIQUE,
  password_hash  TEXT NOT NULL,     -- formato pbkdf2$<iter>$<saltB64>$<hashB64>
  full_name      TEXT NOT NULL DEFAULT '',
  country        TEXT NOT NULL DEFAULT 'INTL' CHECK (country IN ('BR', 'INTL')),
  language       TEXT NOT NULL DEFAULT 'pt',
  email_verified INTEGER NOT NULL DEFAULT 0, -- boolean (0/1)
  soft_delete_at TEXT,                        -- ISO8601, agendamento de hard-delete (GDPR)
  created_at     TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at     TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX users_email_idx ON users(email);
CREATE INDEX users_soft_delete_idx ON users(soft_delete_at) WHERE soft_delete_at IS NOT NULL;

-- Sessão web (substitui o JWT do Supabase Auth) — token opaco, hash guardado
-- aqui, raw só existe no cookie HttpOnly da company. company é a única
-- consumidora (server-to-server); o browser nunca vê o token de sessão do
-- Supabase nem deste.
CREATE TABLE sessions (
  id         TEXT PRIMARY KEY,
  user_id    TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  token_hash TEXT NOT NULL UNIQUE,
  expires_at TEXT NOT NULL,
  revoked_at TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  last_used_at TEXT
);

CREATE INDEX sessions_user_id_idx ON sessions(user_id);
CREATE INDEX sessions_token_hash_idx ON sessions(token_hash);

-- Tokens de verificação de email / magic link — uso único, TTL curto.
CREATE TABLE email_verifications (
  id          TEXT PRIMARY KEY,
  user_id     TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  token_hash  TEXT NOT NULL UNIQUE,
  purpose     TEXT NOT NULL CHECK (purpose IN ('verify_email', 'magic_link')),
  expires_at  TEXT NOT NULL,
  used_at     TEXT,
  created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX email_verifications_user_id_idx ON email_verifications(user_id);

-- Token de licença (VECTORA_TOKEN) — show-once: `token` some depois da
-- primeira revelação, só `token_hash` permanece (comparação em validate).
CREATE TABLE tokens (
  id         TEXT PRIMARY KEY,
  user_id    TEXT NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
  token      TEXT,               -- NULL depois do primeiro reveal
  token_hash TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX tokens_hash_idx ON tokens(token_hash);

CREATE TABLE subscriptions (
  id                  TEXT PRIMARY KEY,
  user_id             TEXT NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
  tier                TEXT NOT NULL DEFAULT 'free' CHECK (tier IN ('free', 'pro')),
  status              TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('trialing','active','past_due','canceled','expired')),
  currency            TEXT NOT NULL DEFAULT 'BRL' CHECK (currency IN ('BRL', 'USD')),
  provider            TEXT CHECK (provider IN ('asaas', 'stripe')),
  provider_id         TEXT,
  customer_id         TEXT,
  started_at          TEXT NOT NULL DEFAULT (datetime('now')),
  trial_ends_at       TEXT,       -- NULL pra free (permanente, sem trial)
  current_period_end  TEXT,
  canceled_at         TEXT,
  created_at          TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at          TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE license_checks (
  id              TEXT PRIMARY KEY,
  user_id         TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  vectora_version TEXT NOT NULL,
  result          TEXT NOT NULL CHECK (result IN ('valid', 'invalid', 'expired', 'not_found')),
  ip              TEXT,
  checked_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX license_checks_user_id_idx ON license_checks(user_id);

CREATE TABLE payment_events (
  id           TEXT PRIMARY KEY,
  user_id      TEXT REFERENCES users(id) ON DELETE SET NULL,
  provider     TEXT NOT NULL CHECK (provider IN ('asaas', 'stripe')),
  event_type   TEXT NOT NULL,
  payload      TEXT NOT NULL DEFAULT '{}', -- JSON serializado (D1 não tem JSONB)
  processed_at TEXT,
  created_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE api_keys (
  id           TEXT PRIMARY KEY,
  user_id      TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name         TEXT NOT NULL,
  scopes       TEXT NOT NULL DEFAULT '["read"]', -- JSON array serializado
  key_hash     TEXT NOT NULL,
  key_prefix   TEXT NOT NULL DEFAULT 'vk_',
  last_used_at TEXT,
  revoked_at   TEXT,
  created_at   TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE (user_id, name)
);

CREATE INDEX api_keys_user_id_idx ON api_keys(user_id);
CREATE INDEX api_keys_hash_idx ON api_keys(key_hash);

CREATE TABLE waitlist (
  id         TEXT PRIMARY KEY,
  email      TEXT NOT NULL UNIQUE,
  source     TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE issues (
  id          TEXT PRIMARY KEY,
  title       TEXT NOT NULL,
  category    TEXT NOT NULL CHECK (category IN ('bug', 'feedback', 'feature')),
  description TEXT,
  email       TEXT,
  created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Fase E — biblioteca de bancos RAG pré-indexados (catálogo só-leitura;
-- artefatos de verdade vivem em storage externo, não Cloudflare).
CREATE TABLE rag_packages (
  id             TEXT PRIMARY KEY,
  name           TEXT NOT NULL,
  source_lib     TEXT NOT NULL,
  source_version TEXT NOT NULL,
  size_bytes     INTEGER NOT NULL,
  checksum       TEXT NOT NULL,
  storage_url    TEXT NOT NULL,
  updated_at     TEXT NOT NULL DEFAULT (datetime('now'))
);

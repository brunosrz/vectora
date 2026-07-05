-- RBAC simples (role) + catálogo de planos por duração + cupons de
-- desconto/gratuidade + presentes de licença por email.
--
-- SQLite não altera CHECK constraints in-place — para acrescentar 'gift'
-- ao CHECK de subscriptions.provider, a tabela é recriada (RENAME →
-- CREATE com o CHECK novo → INSERT SELECT → DROP), preservando dados e
-- FKs de todas as tabelas que referenciam subscriptions indiretamente
-- (nenhuma hoje referencia subscriptions.id diretamente).

ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'user'
  CHECK (role IN ('user', 'admin'));

-- Catálogo de planos por duração. stripe_price_id é preenchido sob
-- demanda (lazy) no primeiro checkout daquele plano em USD — ver
-- services/src/billing/plans.ts (ensureStripePrice).
CREATE TABLE plans (
  id                TEXT PRIMARY KEY,      -- "1m" | "3m" | "6m" | "12m" | "36m"
  months            INTEGER NOT NULL,
  price_usd_cents   INTEGER NOT NULL,
  price_brl_cents   INTEGER NOT NULL,
  stripe_price_id   TEXT,
  active            INTEGER NOT NULL DEFAULT 1
);

INSERT INTO plans (id, months, price_usd_cents, price_brl_cents) VALUES
  ('1m',  1,   900,  2400),
  ('3m',  3,  2700,  7200),
  ('6m',  6,  5100, 13600),
  ('12m', 12, 9600, 25600),
  ('36m', 36, 25900, 69100);

-- Cupons: 'discount' cobra charge_plan_id mas concede grant_plan_id
-- (ex.: cobra 1m, concede 3m); 'free_lifetime' não cobra nada, concede
-- Pro vitalício e é de uso único por padrão (max_redemptions).
CREATE TABLE coupons (
  id                TEXT PRIMARY KEY,
  code              TEXT NOT NULL UNIQUE,  -- normalizado uppercase na aplicação
  kind              TEXT NOT NULL CHECK (kind IN ('discount', 'free_lifetime')),
  grant_plan_id     TEXT REFERENCES plans(id),
  charge_plan_id    TEXT REFERENCES plans(id),
  max_redemptions   INTEGER,               -- NULL = ilimitado
  times_redeemed    INTEGER NOT NULL DEFAULT 0,
  active            INTEGER NOT NULL DEFAULT 1,
  created_by        TEXT NOT NULL REFERENCES users(id),
  expires_at        TEXT,
  created_at        TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX coupons_code_idx ON coupons(code);

CREATE TABLE coupon_redemptions (
  id          TEXT PRIMARY KEY,
  coupon_id   TEXT NOT NULL REFERENCES coupons(id) ON DELETE CASCADE,
  user_id     TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  redeemed_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX coupon_redemptions_coupon_idx ON coupon_redemptions(coupon_id);

-- Presentes de licença — concedidos por email, antes mesmo de existir
-- conta (aplicado no signup se ainda 'pending').
CREATE TABLE gifts (
  id               TEXT PRIMARY KEY,
  email            TEXT NOT NULL,
  granted_by       TEXT NOT NULL REFERENCES users(id),
  duration_months  INTEGER,          -- NULL = vitalício
  status           TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'claimed')),
  claimed_user_id  TEXT REFERENCES users(id),
  claimed_at       TEXT,
  created_at       TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX gifts_email_idx ON gifts(email);

-- subscriptions.provider ganha 'gift' (presentes e cupons free_lifetime
-- não passam por Asaas/Stripe).
ALTER TABLE subscriptions RENAME TO subscriptions_old;

CREATE TABLE subscriptions (
  id                  TEXT PRIMARY KEY,
  user_id             TEXT NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
  tier                TEXT NOT NULL DEFAULT 'free' CHECK (tier IN ('free', 'pro')),
  status              TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('trialing','active','past_due','canceled','expired')),
  currency            TEXT NOT NULL DEFAULT 'BRL' CHECK (currency IN ('BRL', 'USD')),
  provider            TEXT CHECK (provider IN ('asaas', 'stripe', 'gift')),
  provider_id         TEXT,
  customer_id         TEXT,
  started_at          TEXT NOT NULL DEFAULT (datetime('now')),
  trial_ends_at       TEXT,
  current_period_end  TEXT,
  canceled_at         TEXT,
  created_at          TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at          TEXT NOT NULL DEFAULT (datetime('now'))
);

INSERT INTO subscriptions
  (id, user_id, tier, status, currency, provider, provider_id, customer_id,
   started_at, trial_ends_at, current_period_end, canceled_at, created_at, updated_at)
SELECT
  id, user_id, tier, status, currency, provider, provider_id, customer_id,
  started_at, trial_ends_at, current_period_end, canceled_at, created_at, updated_at
FROM subscriptions_old;

DROP TABLE subscriptions_old;

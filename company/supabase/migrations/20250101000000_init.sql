-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ─────────────────────────────────────────────
-- profiles
-- ─────────────────────────────────────────────
CREATE TABLE public.profiles (
  id              UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  full_name       TEXT,
  country         TEXT CHECK (country IN ('BR', 'INTL')) NOT NULL DEFAULT 'INTL',
  language        TEXT DEFAULT 'pt',
  soft_delete_at  TIMESTAMPTZ,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "profiles: own row only"
  ON public.profiles
  FOR ALL
  USING (id = auth.uid())
  WITH CHECK (id = auth.uid());

-- ─────────────────────────────────────────────
-- tokens  (show-once)
-- ─────────────────────────────────────────────
CREATE TABLE public.tokens (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID NOT NULL UNIQUE REFERENCES auth.users(id) ON DELETE CASCADE,
  token       TEXT,                         -- raw token (nulled after first reveal)
  token_hash  TEXT NOT NULL,                -- sha-256 hash stays permanently
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.tokens ENABLE ROW LEVEL SECURITY;

-- tokens are managed exclusively via service role (adminClient)
-- no client-side access allowed
CREATE POLICY "tokens: deny all client access"
  ON public.tokens
  FOR ALL
  USING (false);

-- ─────────────────────────────────────────────
-- subscriptions
-- ─────────────────────────────────────────────
CREATE TABLE public.subscriptions (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id           UUID NOT NULL UNIQUE REFERENCES auth.users(id) ON DELETE CASCADE,
  tier              TEXT NOT NULL CHECK (tier IN ('plus', 'pro')) DEFAULT 'plus',
  status            TEXT NOT NULL CHECK (status IN ('trialing','active','past_due','canceled','expired')) DEFAULT 'trialing',
  currency          TEXT NOT NULL CHECK (currency IN ('BRL', 'USD')) DEFAULT 'BRL',
  provider          TEXT CHECK (provider IN ('asaas', 'stripe')),
  provider_id       TEXT,                   -- Stripe subscription ID / Asaas payment ID
  customer_id       TEXT,                   -- Stripe/Asaas customer ID
  started_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  trial_ends_at     TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '30 days'),
  current_period_end TIMESTAMPTZ,
  canceled_at       TIMESTAMPTZ,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.subscriptions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "subscriptions: own row only"
  ON public.subscriptions
  FOR SELECT
  USING (user_id = auth.uid());

-- ─────────────────────────────────────────────
-- license_checks
-- ─────────────────────────────────────────────
CREATE TABLE public.license_checks (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id          UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  vectora_version  TEXT NOT NULL,
  result           TEXT NOT NULL CHECK (result IN ('valid', 'invalid', 'expired', 'not_found')),
  ip               TEXT,
  checked_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.license_checks ENABLE ROW LEVEL SECURITY;

CREATE POLICY "license_checks: own rows only"
  ON public.license_checks
  FOR SELECT
  USING (user_id = auth.uid());

CREATE INDEX license_checks_user_id_idx ON public.license_checks(user_id);

-- ─────────────────────────────────────────────
-- payment_events
-- ─────────────────────────────────────────────
CREATE TABLE public.payment_events (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id      UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  provider     TEXT NOT NULL CHECK (provider IN ('asaas', 'stripe')),
  event_type   TEXT NOT NULL,
  payload      JSONB NOT NULL DEFAULT '{}',
  processed_at TIMESTAMPTZ,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.payment_events ENABLE ROW LEVEL SECURITY;

-- payment_events are service-role only
CREATE POLICY "payment_events: deny client access"
  ON public.payment_events
  FOR ALL
  USING (false);

-- ─────────────────────────────────────────────
-- api_keys
-- ─────────────────────────────────────────────
CREATE TABLE public.api_keys (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id      UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  name         TEXT NOT NULL,
  scopes       TEXT[] NOT NULL DEFAULT '{"read"}',
  key_hash     TEXT NOT NULL,               -- sha-256 of raw key
  key_prefix   TEXT NOT NULL DEFAULT 'vk_',
  last_used_at TIMESTAMPTZ,
  revoked_at   TIMESTAMPTZ,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT api_keys_name_user_unique UNIQUE (user_id, name)
);

ALTER TABLE public.api_keys ENABLE ROW LEVEL SECURITY;

CREATE POLICY "api_keys: own rows only"
  ON public.api_keys
  FOR SELECT
  USING (user_id = auth.uid());

CREATE INDEX api_keys_user_id_idx ON public.api_keys(user_id);
CREATE INDEX api_keys_hash_idx    ON public.api_keys(key_hash);

-- ─────────────────────────────────────────────
-- waitlist  (leads)
-- ─────────────────────────────────────────────
CREATE TABLE public.waitlist (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email      TEXT NOT NULL UNIQUE,
  source     TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.waitlist ENABLE ROW LEVEL SECURITY;

-- waitlist inserts via service role only
CREATE POLICY "waitlist: deny client access"
  ON public.waitlist
  FOR ALL
  USING (false);

-- ─────────────────────────────────────────────
-- issues
-- ─────────────────────────────────────────────
CREATE TABLE public.issues (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title       TEXT NOT NULL,
  category    TEXT NOT NULL CHECK (category IN ('bug', 'feedback', 'feature')),
  description TEXT NOT NULL,
  email       TEXT,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.issues ENABLE ROW LEVEL SECURITY;

CREATE POLICY "issues: deny client access"
  ON public.issues
  FOR ALL
  USING (false);

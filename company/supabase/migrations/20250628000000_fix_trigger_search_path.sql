-- Fix: adicionar schema 'extensions' ao search_path do trigger.
-- No Supabase, pgcrypto (gen_random_bytes, digest) fica em 'extensions',
-- não em 'public'. SECURITY DEFINER com SET search_path = public não enxerga
-- essas funções, causando "Database error saving new user" no signup.

CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, extensions
AS $$
DECLARE
  raw_token TEXT;
  token_hash TEXT;
BEGIN
  -- 1. Create profile
  INSERT INTO public.profiles (id, full_name, country)
  VALUES (
    NEW.id,
    COALESCE(NEW.raw_user_meta_data->>'full_name', ''),
    COALESCE(NEW.raw_user_meta_data->>'country', 'INTL')
  )
  ON CONFLICT (id) DO NOTHING;

  -- 2. Generate token (raw will be revealed once, then nulled)
  raw_token := encode(gen_random_bytes(32), 'hex');
  token_hash := encode(digest(raw_token, 'sha256'), 'hex');

  INSERT INTO public.tokens (user_id, token, token_hash)
  VALUES (NEW.id, raw_token, token_hash)
  ON CONFLICT (user_id) DO NOTHING;

  -- 3. Create subscription (trialing, 30 days)
  INSERT INTO public.subscriptions (
    user_id, tier, status, currency, trial_ends_at
  )
  VALUES (
    NEW.id,
    'plus',
    'trialing',
    CASE WHEN COALESCE(NEW.raw_user_meta_data->>'country', 'INTL') = 'BR' THEN 'BRL' ELSE 'USD' END,
    NOW() + INTERVAL '30 days'
  )
  ON CONFLICT (user_id) DO NOTHING;

  RETURN NEW;
END;
$$;

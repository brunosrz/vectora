-- Modelo free/pro: substitui os planos pagos "plus"/"pro" por um tier free
-- (uso local, sem conta) + pro (~R$24/mês, capacidade de time — chat web,
-- convites, SSO/SAML, storage escalável, webhooks, REST API com rate limit
-- maior). Ver documents/plan.md (decisão registrada na sessão de repricing).

-- 1. Dados existentes: quem estava em 'plus' vira 'free'.
UPDATE public.subscriptions SET tier = 'free' WHERE tier = 'plus';

-- 2. Troca a CHECK constraint para o novo domínio de valores.
--    "subscriptions_tier_check" é o nome padrão que o Postgres gera pra um
--    CHECK inline sem nome explícito (confirmado em 20250101000000_init.sql);
--    IF EXISTS é só uma salvaguarda extra.
ALTER TABLE public.subscriptions DROP CONSTRAINT IF EXISTS subscriptions_tier_check;
ALTER TABLE public.subscriptions
  ADD CONSTRAINT subscriptions_tier_check CHECK (tier IN ('free', 'pro'));
ALTER TABLE public.subscriptions ALTER COLUMN tier SET DEFAULT 'free';

-- 3. Free é permanente (sem trial a expirar) — usuários free ficam 'active'
--    direto, sem contagem regressiva. trial_ends_at só importa pra quem
--    está efetivamente em trial de pro (fluxo futuro), então relaxamos o
--    NOT NULL/default: fica NULL pra quem nunca teve um trial de pro.
ALTER TABLE public.subscriptions ALTER COLUMN trial_ends_at DROP NOT NULL;
ALTER TABLE public.subscriptions ALTER COLUMN trial_ends_at DROP DEFAULT;
UPDATE public.subscriptions
  SET trial_ends_at = NULL, status = 'active'
  WHERE tier = 'free' AND status = 'trialing';

-- 4. Trigger de signup: novo usuário nasce 'free'/'active' (sem trial),
--    upgrade pra 'pro' acontece só via checkout (create-checkout function).
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

  -- 3. Free tier — permanente, sem trial/expiração.
  INSERT INTO public.subscriptions (
    user_id, tier, status, currency, trial_ends_at
  )
  VALUES (
    NEW.id,
    'free',
    'active',
    CASE WHEN COALESCE(NEW.raw_user_meta_data->>'country', 'INTL') = 'BR' THEN 'BRL' ELSE 'USD' END,
    NULL
  )
  ON CONFLICT (user_id) DO NOTHING;

  RETURN NEW;
END;
$$;

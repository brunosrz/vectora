-- Concede role admin + Pro vitalício ao criador do Vectora. Se a conta
-- ainda não existir no momento do deploy, os UPDATEs abaixo são no-op
-- silencioso (WHERE não bate linha nenhuma) — aplicar manualmente via
-- `wrangler d1 execute vectora-db --remote --command "..."` depois que a
-- conta existir (mesmos dois comandos, documentado no plano de
-- verificação da feature).

UPDATE users SET role = 'admin'
WHERE email = 'bruno.soarxz@gmail.com';

INSERT INTO subscriptions (id, user_id, tier, status, provider, current_period_end)
SELECT lower(hex(randomblob(16))), id, 'pro', 'active', 'gift', NULL
FROM users
WHERE email = 'bruno.soarxz@gmail.com'
ON CONFLICT (user_id) DO UPDATE SET
  tier = 'pro',
  status = 'active',
  provider = 'gift',
  current_period_end = NULL,
  updated_at = datetime('now');

-- gh-bot self-hosted: usuário roda a revisão na própria instância Vectora
-- (via túnel do gateway, `tokens.token` do mesmo user_id) em vez do runner
-- efêmero do GitHub Actions. `0001_schema.sql` já foi aplicada em bancos
-- provisionados antes desta feature — ao contrário das tabelas em
-- `CREATE TABLE IF NOT EXISTS` daquele arquivo, esta migração roda
-- exatamente uma vez por banco (D1 rastreia via `d1_migrations`), então
-- `ALTER TABLE`/`CREATE TABLE` aqui não precisam ser idempotentes.

ALTER TABLE gha_bot_config ADD COLUMN self_hosted_enabled INTEGER NOT NULL DEFAULT 0;

-- Job assíncrono de revisão rodada na instância Vectora do próprio usuário
-- (modo self-hosted) — a Action cria com POST /gha-bot/review e recebe
-- 202+job_id na hora (o job em si é despachado pro backend Python via
-- fire-and-forget pelo túnel do gateway, sidesteps o teto de 30s do
-- GatewaySession, que é pra request/response HTTP síncrono, não pra isto),
-- depois faz long-poll em GET /gha-bot/review/:id até status != 'pending'.
-- O backend Python chama POST /gha-bot/review/:id/result quando termina —
-- fora do túnel (outbound normal, sem problema de NAT).
--
-- `callback_secret`: gerado no INSERT (POST /gha-bot/review), entregue só
-- dentro do payload `review_job` pelo túnel do gateway (nunca na resposta
-- HTTP da Action, que aparece em logs de workflow) — POST .../result exige
-- este secret via Bearer, senão job_id sozinho (visível em log público)
-- bastaria pra qualquer um escrever review_text arbitrário no PR.
CREATE TABLE gha_bot_review_jobs (
  id              TEXT PRIMARY KEY,
  user_id         TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  callback_secret TEXT NOT NULL,
  status          TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'done', 'failed')),
  review_text     TEXT,
  error           TEXT,
  created_at      TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX gha_bot_review_jobs_user_id_idx ON gha_bot_review_jobs(user_id);

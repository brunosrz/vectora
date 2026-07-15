-- Resposta do admin a uma issue + status. 'open' por padrão (badge de
-- notificação in-app no admin conta issues nesse status); 'resolved' quando
-- o admin responde/marca como resolvida. response/responded_at NULL até a
-- primeira resposta.
ALTER TABLE issues ADD COLUMN status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'resolved'));
ALTER TABLE issues ADD COLUMN response TEXT;
ALTER TABLE issues ADD COLUMN responded_at TEXT;

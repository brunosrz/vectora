-- Migration 0003: promove o modo da sessão (chat/code) a coluna de 1ª classe.
-- Antes vivia em extra->>'mode'; o modo "dev" foi renomeado para "code".

-- up
ALTER TABLE vectora_sessions
    ADD COLUMN IF NOT EXISTS mode TEXT NOT NULL DEFAULT 'code';

-- Backfill a partir de extra: "chat" preserva; "dev"/ausente viram "code".
UPDATE vectora_sessions
SET mode = CASE WHEN extra->>'mode' = 'chat' THEN 'chat' ELSE 'code' END;

CREATE INDEX IF NOT EXISTS idx_sessions_mode ON vectora_sessions(mode);

-- down
DROP INDEX IF EXISTS idx_sessions_mode;
ALTER TABLE vectora_sessions DROP COLUMN IF EXISTS mode;

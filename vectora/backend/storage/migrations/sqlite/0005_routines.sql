-- up
CREATE TABLE IF NOT EXISTS vectora_routines (
    id           TEXT PRIMARY KEY,
    user_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name         TEXT NOT NULL,
    instruction  TEXT NOT NULL,
    cron_expr    TEXT NOT NULL,
    workspace_id TEXT,
    enabled      INTEGER NOT NULL DEFAULT 1,
    last_run_at  TEXT,
    next_run_at  TEXT,
    created_at   TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

-- down
DROP TABLE IF EXISTS vectora_routines;

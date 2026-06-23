-- up
CREATE TABLE IF NOT EXISTS vectora_background_tasks (
    id             TEXT PRIMARY KEY,
    session_id     TEXT NOT NULL,
    workspace_id   TEXT,
    user_id        TEXT NOT NULL,
    kind           TEXT NOT NULL,
    name           TEXT NOT NULL,
    instruction    TEXT NOT NULL,
    trigger_type   TEXT NOT NULL,
    trigger_config TEXT NOT NULL DEFAULT '{}',
    enabled        INTEGER NOT NULL DEFAULT 1,
    last_run_at    TEXT,
    next_run_at    TEXT,
    created_at     TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at     TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_background_tasks_session ON vectora_background_tasks(session_id);
CREATE INDEX IF NOT EXISTS idx_background_tasks_due     ON vectora_background_tasks(enabled, trigger_type);

CREATE TABLE IF NOT EXISTS vectora_background_runs (
    id             TEXT PRIMARY KEY,
    task_id        TEXT NOT NULL,
    session_id     TEXT NOT NULL,
    run_thread_id  TEXT,
    trigger_source TEXT NOT NULL,
    status         TEXT NOT NULL DEFAULT 'running',
    summary        TEXT,
    started_at     TEXT NOT NULL DEFAULT (datetime('now')),
    finished_at    TEXT
);

CREATE INDEX IF NOT EXISTS idx_background_runs_task    ON vectora_background_runs(task_id);
CREATE INDEX IF NOT EXISTS idx_background_runs_session ON vectora_background_runs(session_id);

-- down
DROP TABLE IF EXISTS vectora_background_runs;
DROP TABLE IF EXISTS vectora_background_tasks;

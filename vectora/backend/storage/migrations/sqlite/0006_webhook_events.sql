-- up
CREATE TABLE IF NOT EXISTS webhook_events (
    id           TEXT PRIMARY KEY,
    provider     TEXT NOT NULL,
    event_type   TEXT NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    workspace_id TEXT,
    received_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_webhook_events_provider    ON webhook_events(provider);
CREATE INDEX IF NOT EXISTS idx_webhook_events_received_at ON webhook_events(received_at DESC);
CREATE INDEX IF NOT EXISTS idx_webhook_events_workspace   ON webhook_events(workspace_id);

-- down
DROP TABLE IF EXISTS webhook_events;

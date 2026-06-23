-- up
CREATE TABLE IF NOT EXISTS email_events (
    id           TEXT PRIMARY KEY,
    provider     TEXT NOT NULL,
    event_type   TEXT NOT NULL,
    from_email   TEXT,
    to_email     TEXT,
    subject      TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    received_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_email_events_provider    ON email_events(provider);
CREATE INDEX IF NOT EXISTS idx_email_events_received_at ON email_events(received_at DESC);
CREATE INDEX IF NOT EXISTS idx_email_events_event_type  ON email_events(event_type);

-- down
DROP TABLE IF EXISTS email_events;

CREATE TABLE IF NOT EXISTS `PendingObservation` (
    id INTEGER PRIMARY KEY,
    observation TEXT NOT NULL,
    topic TEXT NOT NULL,
    error_type TEXT,
    error_message TEXT,
    status_code INTEGER,
    retry_count INT,
    last_retry TEXT NOT NULL DEFAULT current_timestamp,
);
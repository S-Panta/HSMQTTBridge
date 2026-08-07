CREATE TABLE IF NOT EXISTS `PendingObservation` (
    id INTEGER PRIMARY KEY,
    observation TEXT NOT NULL,
    status_code INTEGER NOT NULL
);
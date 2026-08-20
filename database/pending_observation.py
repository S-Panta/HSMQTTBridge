import json
import sqlite3
from database.model import PendingObservation


class PendingObservationStore:
    """Class to wrap SQLite database operations."""

    def __init__(self, path):
        self.path = path

        try:
            with sqlite3.connect(self.path) as connection:
                connection.execute("PRAGMA journal_mode = WAL")
                self._initialize_db(connection)

            print("Connected to sqlite database is successful")

        except sqlite3.Error as e:
            print(f"Connected to sqlite database failed: {e}")

    def _initialize_db(self, connection):
        connection.execute("""
            CREATE TABLE IF NOT EXISTS PendingObservation (
                id INTEGER PRIMARY KEY,
                observation TEXT NOT NULL,
                topic TEXT NOT NULL,
                error_type TEXT,
                error_message TEXT,
                status_code INTEGER,
                retry_count INTEGER NOT NULL DEFAULT 0,
                last_retry TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

    def insert(self, observation, topic, error):
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                """
                INSERT INTO PendingObservation (
                    topic,
                    observation,
                    error_type,
                    error_message,
                    status_code
                )
                VALUES (?, ?,?, ?, ?)
                """,
                (
                    topic,
                    json.dumps(observation),
                    error.error_type,
                    error.error_message,
                    error.status_code,
                ),
            )

    def fetch_all(self):
        with sqlite3.connect(self.path) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute("""
                SELECT
                    id,
                    observation,
                    topic,
                    error_type,
                    error_message,
                    status_code,
                    retry_count,
                    last_retry
                FROM PendingObservation
                ORDER BY id ASC
            """).fetchall()
            return [
                PendingObservation(
                    id=row["id"],
                    observation=json.loads(row["observation"]),
                    topic=row["topic"],
                    error_type=row["error_type"],
                    error_message=row["error_message"],
                    status_code=row["status_code"],
                    retry_count=row["retry_count"],
                )
                for row in rows
            ]

    def delete(self, observation_id):
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                "DELETE FROM PendingObservation WHERE id = ?", (observation_id,)
            )

    def mark_observation_as_pending(self, observation_id, error):
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                """
                        UPDATE PendingObservation
                        SET retry_count = retry_count + 1,
                            last_retry = CURRENT_TIMESTAMP,
                            error_type = ?,
                            error_message = ?,
                            status_code = ?
                        WHERE id = ?
                        """,
                (
                    error.error_type,
                    error.error_message,
                    error.status_code,
                    observation_id,
                ),
            )

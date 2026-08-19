import json
import sqlite3


class PendingObservation:
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

    def insert_observation(self, observation, topic, error):
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

    def get_all_observation(self):
        with sqlite3.connect(self.path) as connection:
            cursor = connection.execute("""SELECT id, observation, topic, retry_count 
                FROM PendingObservation ORDER BY id ASC
                """)
            return cursor.fetchall()

    def delete_observation(self, row_id):
        with sqlite3.connect(self.path) as connection:
            connection.execute("DELETE FROM PendingObservation WHERE id = ?", (row_id,))

    def mark_observation_as_pending(self, row_id, error):
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
                    row_id,
                ),
            )

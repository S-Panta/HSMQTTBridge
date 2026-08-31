import json
import logging
import sqlite3
from database.model import FailedObservation

logger = logging.getLogger(__name__)


class FailedObservationStore:
    """Class to wrap SQLite database operations."""

    def __init__(self, path):
        self.path = path

        try:
            with sqlite3.connect(self.path) as connection:
                connection.execute("PRAGMA journal_mode = WAL")
                logger.info("Connected to sqlite database: %s", self.path)
                self._initialize_db(connection)

        except sqlite3.Error as err:
            logger.exception(
                "Failed to connect to sqlite database: %s . Errortype: %s .  Error %s",
                self.path,
                type(err).__name__,
                err,
            )

    def _initialize_db(self, connection):
        connection.execute("""
            CREATE TABLE IF NOT EXISTS failed_observation (
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
        logger.info("Initialized failed_observation table")

    def insert(self, observation, topic, error):
        try:
            with sqlite3.connect(self.path) as connection:
                connection.execute(
                    """
                    INSERT INTO failed_observation (
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
                logger.info(
                    "Successfully inserted failed observation for topic=%s",
                    topic,
                )
        except sqlite3.Error:
            logger.exception(
                "Failed to insert failed observation for topic=%s",
                topic,
            )
            raise

    def fetch_all(self):
        try:
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
                    FROM failed_observation
                    ORDER BY id ASC
                """).fetchall()
                return [
                    FailedObservation(
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
        except sqlite3.Error:
            logger.exception("Failed to fetch failed observations")
            raise

    def delete(self, observations):
        if not observations:
            return
        try:
            with sqlite3.connect(self.path) as connection:
                connection.executemany(
                    "DELETE FROM failed_observation WHERE id = ?",
                    ((observation.id,) for observation in observations),
                )
        except sqlite3.Error:
            logger.exception(
                "Failed to delete %d failed observation(s)", len(observations)
            )
            raise

    def update_observation_retry_count(self, observations, error):
        if not observations:
            return
        try:
            with sqlite3.connect(self.path) as connection:
                connection.executemany(
                    """
                            UPDATE failed_observation
                            SET retry_count = retry_count + 1,
                                last_retry = CURRENT_TIMESTAMP,
                                error_type = ?,
                                error_message = ?,
                                status_code = ?
                            WHERE id = ?
                            """,
                    (
                        (
                            error.error_type,
                            error.error_message,
                            error.status_code,
                            observation.id,
                        )
                        for observation in observations
                    ),
                )
        except sqlite3.Error:
            logger.exception(
                "Failed to update retry count for %d observation(s)",
                len(observations),
            )
            raise

import json
import logging
import sqlite3
from database.model import BufferedObservation

logger = logging.getLogger(__name__)


class RetryBuffer:
    """This class contains methods for working with retry buffer"""

    def __init__(self, path):
        self.path = path
        self.database_table = "buffered_observations"

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
        connection.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.database_table} (
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
        logger.info("Initialized buffered_observation table")

    def insert(self, observation, topic, error):
        try:
            with sqlite3.connect(self.path) as connection:
                connection.execute(
                    f"""
                    INSERT INTO {self.database_table} (
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
                    "Successfully inserted for topic=%s",
                    topic,
                )
        except sqlite3.Error:
            logger.exception(
                "Failed to insert for topic=%s",
                topic,
            )
            raise

    def fetch_all(self):
        try:
            with sqlite3.connect(self.path) as connection:
                connection.row_factory = sqlite3.Row
                rows = connection.execute(f"""
                    SELECT
                        id,
                        observation,
                        topic,
                        error_type,
                        error_message,
                        status_code,
                        retry_count,
                        last_retry
                    FROM {self.database_table}
                    ORDER BY id ASC
                """).fetchall()
                return [
                    BufferedObservation(
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
            logger.exception("Failed to fetch %s table", {self.database_table})
            raise

    def delete(self, observations):
        if not observations:
            return
        try:
            with sqlite3.connect(self.path) as connection:
                connection.executemany(
                    f"DELETE FROM {self.database_table} WHERE id = ?",
                    ((observation.id,) for observation in observations),
                )
        except sqlite3.Error:
            logger.exception("Failed to delete %d observations", len(observations))
            raise

    def update_observation_retry_count(self, observations, error):
        if not observations:
            return
        try:
            with sqlite3.connect(self.path) as connection:
                connection.executemany(
                    f"""
                            UPDATE {self.database_table}
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
                "Failed to update retry count for %d observation",
                len(observations),
            )
            raise

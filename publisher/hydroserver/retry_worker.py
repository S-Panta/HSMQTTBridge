# pylint: disable=broad-exception-caught
from collections import defaultdict
import logging
import threading

logger = logging.getLogger(__name__)


class RetryWorker:
    """class for implementation of retry worker"""

    # This class should know which service the data is being retried to and the cache

    def __init__(self, database, hydroserver, retry_interval, max_retry_attempt):
        self.database = database
        self.hydroserver_publisher = hydroserver
        self.retry_interval = retry_interval
        self.max_retry_attempt = max_retry_attempt
        self._stop_event = threading.Event()

    def run(self):
        while not self._stop_event.is_set():
            try:
                logger.info(
                    "Running retry worker every %s seconds", self.retry_interval
                )
                self.post_into_hydroserver()
            except Exception as e:
                logger.exception("Retry worker error: %s", e)
            self._stop_event.wait(self.retry_interval)

    def stop(self):
        # Unblocks the worker thread
        logger.info("Stopping retry worker")
        self._stop_event.set()

    def __get_failed_observations(self):
        return self.database.fetch_all()

    def __group_observations_by_topic(self, observations):
        chunks = defaultdict(list)
        for observation in observations:
            if observation.retry_count >= self.max_retry_attempt:
                logger.warning(
                    "Skipping observation for topic '%s': "
                    "maximum retry attempts (%d) reached",
                    observation.topic,
                    self.max_retry_attempt,
                )
                continue
            chunks[observation.topic].append(observation)
        return chunks

    def post_into_hydroserver(self):
        observations = self.__get_failed_observations()
        if not observations:
            logger.info("No observation exists in the cache")
            return
        chunks = self.__group_observations_by_topic(observations)
        logger.info("There are %d chunks to process", len(chunks))
        for i, (topic, chunk) in enumerate(chunks.items(), start=1):
            try:
                logger.info(
                    "Posting chunk %d/%d - Topic: %s (%d observations) "
                    "to HydroServer",
                    i,
                    len(chunks),
                    topic,
                    len(chunk),
                )
                result = self.hydroserver_publisher.batch_upload(chunk)
                # A successful hydroserver post returns no value
                if result is not None:
                    self.database.update_observation_retry_count(chunk, result)
                else:
                    # once successful post is done, the data is deleted from local database
                    logger.info(
                        "Successfully posted chunk %d/%d for topic '%s'. "
                        "Deleting observations from local database.",
                        i,
                        len(chunks),
                        topic,
                    )
                    self.database.delete(chunk)
            except Exception as e:
                logger.exception(
                    "Error processing chunk %d/%d for topic '%s' . Error is %s",
                    i,
                    len(chunks),
                    topic,
                    e,
                )

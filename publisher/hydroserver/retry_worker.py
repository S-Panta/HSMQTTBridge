# pylint: disable=broad-exception-caught
from collections import defaultdict
import logging
import threading

logger = logging.getLogger(__name__)


class RetryWorker:
    """class for implementation of retry worker"""

    MAX_ATTENPTS = 4

    def __init__(self, database, hydroserver, interval=30):
        self.database = database
        self.hydroserver_publisher = hydroserver
        self.interval = interval
        self._stop_event = threading.Event()

    def run(self):
        while not self._stop_event.is_set():
            try:
                logging.info("Running retry worker")
                self.post_into_hydroserver()
            except Exception as e:
                logger.exception("Retry worker error: %s", e)
            self._stop_event.wait(self.interval)

    def stop(self):
        # Unblocks the worker thread
        logger.info("Stopping retry worker")
        self._stop_event.set()

    def __get_failed_observations(self):
        return self.database.fetch_all()

    def __group_observations_by_topic(self, observations):
        chunks = defaultdict(list)
        for observation in observations:
            if observation.retry_count >= self.MAX_ATTENPTS:
                logger.warning(
                    "Skipping observation for topic '%s': "
                    "maximum retry attempts (%d) reached",
                    observation.topic,
                    self.MAX_ATTENPTS,
                )
                continue
            chunks[observation.topic].append(observation)
        return chunks

    def post_into_hydroserver(self):
        observations = self.__get_failed_observations()
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

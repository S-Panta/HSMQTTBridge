# pylint: disable=broad-exception-caught
from collections import defaultdict
import logging
import threading

logger = logging.getLogger(__name__)


class RetryWorker:
    """class for implementation of retry worker"""

    # This class should know which service the data is being retried to and the cache

    def __init__(
        self, retry_buffer, hydroserver_publisher, retry_interval, max_retry_attempt
    ):
        self.retry_buffer = retry_buffer
        self.hydroserver_publisher = hydroserver_publisher
        self.retry_interval = retry_interval
        self.max_retry_attempt = max_retry_attempt
        self._stop_event = threading.Event()

    def run(self):
        while not self._stop_event.is_set():
            try:
                logger.info(
                    "Running retry worker every %s seconds", self.retry_interval
                )
                self.post_buffered_observation_to_hydroserver()
            except Exception as e:
                logger.exception("Retry worker error: %s", e)
            self._stop_event.wait(self.retry_interval)

    def stop(self):
        logger.info("Stopping retry worker")
        self._stop_event.set()

    def _get_observations_from_retry_buffer(self):
        return self.retry_buffer.fetch_all()

    def _filter_observations(self, observations):
        skipped_observation_count_for_retry = 0
        deleted_observation_count = 0
        filtered_observation = []
        for observation in observations:
            if observation.status_code == 404:
                deleted_observation_count += 1
                self.retry_buffer.delete_observation(observation)
                continue
            if observation.retry_count >= self.max_retry_attempt:
                skipped_observation_count_for_retry += 1
                continue

            filtered_observation.append(observation)
        if skipped_observation_count_for_retry:
            logger.info(
                "Skipped %d observations: maximum retry attempts (%d) reached",
                skipped_observation_count_for_retry,
                self.max_retry_attempt,
            )
        if deleted_observation_count:
            logger.info(
                "Deleted %d observations with HTTP 404 status code",
                deleted_observation_count,
            )
        return filtered_observation

    def _group_observations_by_topic(self, observations):
        chunks = defaultdict(list)
        for observation in observations:
            chunks[observation.topic].append(observation)
        return chunks

    def post_buffered_observation_to_hydroserver(self):
        observations = self._get_observations_from_retry_buffer()
        if not observations:
            logger.info("No observation exists in the sqlite buffer")
            return
        filtered_observation = self._filter_observations(observations)
        chunks = self._group_observations_by_topic(filtered_observation)
        logger.info("Total chunks to process from database: %d ", len(chunks))
        for i, (topic, chunk) in enumerate(chunks.items(), start=1):
            try:
                logger.info(
                    "Posting chunk %d/%d : Topic: %s (%d observations) "
                    "to HydroServer",
                    i,
                    len(chunks),
                    topic,
                    len(chunk),
                )
                result = self.hydroserver_publisher.batch_upload(chunk)
                # A successful hydroserver post returns no value
                if result is not None:
                    self.retry_buffer.update_observation_retry_count(chunk, result)
                else:
                    # once successful post is done, the data is deleted from retry buffer
                    logger.info(
                        "Successfully posted chunk %d/%d for topic '%s'. "
                        "Deleting observations from retry buffer.",
                        i,
                        len(chunks),
                        topic,
                    )
                    self.retry_buffer.delete_observations(chunk)
            except Exception as e:
                logger.exception(
                    "Error processing chunk %d/%d for topic '%s' . Error is %s",
                    i,
                    len(chunks),
                    topic,
                    e,
                )

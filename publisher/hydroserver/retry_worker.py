# pylint: disable=broad-exception-caught
from collections import defaultdict
import threading


class RetryWorker:
    """class for implementation of retry worker"""

    MAX_ATTENPTS = 4

    def __init__(self, database, hydroserver, interval=30 * 60):
        self.database = database
        self.hydroserver_publisher = hydroserver
        self.interval = interval
        self._stop_event = threading.Event()

    def run(self):
        while not self._stop_event.is_set():
            try:
                print("Running retry worker")
                self.post_into_hydroserver()
            except Exception as e:
                print(f"Retry worker error: {e}")
            self._stop_event.wait(self.interval)

    def stop(self):
        # Unblocks the worker thread
        self._stop_event.set()

    def __get_failed_observations(self):
        return self.database.fetch_all()

    def __group_observations_by_topic(self, observations):
        chunks = defaultdict(list)
        for observation in observations:
            if observation.retry_count >= self.MAX_ATTENPTS:
                print("skipping the post observation to hydroserver")
                continue
            chunks[observation.topic].append(observation)
        return chunks

    def post_into_hydroserver(self):
        observations = self.__get_failed_observations()
        chunks = self.__group_observations_by_topic(observations)
        print(f"There are {len(chunks)} chunks.")
        for i, (topic, chunk) in enumerate(chunks.items(), start=1):
            try:
                print(
                    f"Posting chunk {i}/{len(chunks)} "
                    f" Topic {topic} ({len(chunk)} observations) "
                    f"to HydroServer"
                )
                result = self.hydroserver_publisher.batch_upload(chunk)
                # A successful hydroserver post returns no value
                if result is not None:
                    self.database.update_observation_retry(chunk, result)
                else:
                    # once successful post is done, the data is deleted from local database
                    self.database.delete(chunk)
            except Exception as e:
                print(f"Error processing chunk {i}: {e}")

import os
from collections import defaultdict
from dotenv import load_dotenv
from database.pending_observation import PendingObservationStore
from publisher.hydroserver.hydroserver_publisher import HydroServerPublisher

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

load_dotenv()

HYDROSERVER_URL = os.getenv("HYDROSERVER_URL")
API_KEY = os.getenv("HYDROSERVER_API_KEY")

DB_PATH = os.path.join(PROJECT_DIR, "data", "observation.db")

hydroserver_publisher = HydroServerPublisher(
    HYDROSERVER_URL,
    API_KEY,
)


class RetryWorker:
    """class for implementation of retry worker"""

    def __init__(self):
        self.database = PendingObservationStore(DB_PATH)
        self.hydroserver_publisher = hydroserver_publisher

    def get_pending_observations(self):
        return self.database.fetch_all()

    def __chunk_database_response(self, observations):
        chunk_list = defaultdict(list)
        for observation in observations:
            chunk_list[observation.topic].append(observation)
        return chunk_list

    def repost_into_hydroserver(self):
        observations = self.get_pending_observations()
        chunk_list = self.__chunk_database_response(observations)
        chunks = list(chunk_list.values())
        print(f"there are {len(chunks)} chunks.")
        for i, chunk in enumerate(chunks, start=1):
            print(f"Posting {i} chunks to hydroserver")
            request = hydroserver_publisher.batch_upload(chunk)
            if request is not None:
                self.database.mark_observation_as_pending(chunk, request)
            else:
                self.database.delete(chunk)
            print("one step done; one chunk completed")


worker = RetryWorker()
worker.repost_into_hydroserver()

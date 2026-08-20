import os
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

    def repost_into_hydroserver(self):
        observations = self.get_pending_observations()
        for pending in observations:
            result = hydroserver_publisher.push_observation_to_upstream(
                pending.observation
            )
            if result is None:
                self.database.delete(pending.id)
            else:
                self.database.mark_observation_as_pending(pending.id, result)


worker = RetryWorker()
worker.repost_into_hydroserver()

import os
import logging
import threading


from dotenv import load_dotenv

from database.failed_observation_store import FailedObservationStore
from mqtt.consumer import MQTTClient
from message_router import MessageRouter
from publisher.hydroserver.hydroserver_publisher import HydroServerPublisher
from publisher.hydroserver.retry_worker import RetryWorker

load_dotenv()

HYDROSERVER_URL = os.getenv("HYDROSERVER_URL")
API_KEY = os.getenv("HYDROSERVER_API_KEY")

MQTT_HOST = "localhost"
MQTT_PORT = 1883

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(PROJECT_DIR, "data", "observation.db")

MQTT_TOPIC_FILTER = "uwrl/#"

logger = logging.getLogger(__name__)


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    failed_observation = FailedObservationStore(DB_PATH)
    hydroserver_publisher = HydroServerPublisher(
        HYDROSERVER_URL,
        API_KEY,
    )

    mqtt = MQTTClient(host=MQTT_HOST, port=MQTT_PORT, topic_prefix=MQTT_TOPIC_FILTER)

    router = MessageRouter(hydroserver_publisher, failed_observation)
    worker = threading.Thread(target=router.route_incoming_message, daemon=True)
    worker.start()
    logger.info("Message router started")
    retry_worker = RetryWorker(failed_observation, hydroserver_publisher)
    retry_worker_thread = threading.Thread(target=retry_worker.run, daemon=True)
    retry_worker_thread.start()
    try:
        mqtt.connect()
    finally:
        mqtt.stop()
        retry_worker.stop()
        retry_worker_thread.join(timeout=10)
        logger.info("Service shutdown")


if __name__ == "__main__":
    main()

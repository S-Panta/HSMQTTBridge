import logging
import threading
from config import config

from database.failed_observation_store import FailedObservationStore
from mqtt.consumer import MQTTClient
from message_router import MessageRouter
from publisher.hydroserver.hydroserver_publisher import HydroServerPublisher
from publisher.hydroserver.retry_worker import RetryWorker

logger = logging.getLogger(__name__)


def main():
    logging.basicConfig(
        level=getattr(logging, config.log_level),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    failed_observation = FailedObservationStore(config.db_path)
    hydroserver_publisher = HydroServerPublisher(
        config.hydroserver_url,
        config.workspace_api_key,
    )

    mqtt = MQTTClient(host=config.mqtt_broker_url, port=config.mqtt_broker_port)

    router = MessageRouter(hydroserver_publisher, failed_observation)
    worker = threading.Thread(target=router.route_incoming_message, daemon=True)
    worker.start()
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

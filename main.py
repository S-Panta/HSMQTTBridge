import threading
import logging
from config import config
from database.failed_observation_store import FailedObservationStore
from mqtt.consumer import MQTTConsumer
from message_router import MessageRouter
from publisher.hydroserver.hydroserver_publisher import HydroServerPublisher
from publisher.hydroserver.retry_worker import RetryWorker


def setup_logging():
    root = logging.getLogger()

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(threadName)s - %(message)s"
    )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    root.addHandler(handler)
    root.setLevel(getattr(logging, config.log_level))


def main():
    # setting up logger first
    setup_logging()
    logger = logging.getLogger(__name__)

    failed_observation = FailedObservationStore(config.db_path)
    hydroserver_publisher = HydroServerPublisher(
        config.hydroserver_url,
        config.workspace_api_key,
    )

    mqtt = MQTTConsumer(
        host=config.mqtt_broker_url,
        port=config.mqtt_broker_port,
        topic_filter=config.mqtt_topic_filter,
    )

    router = MessageRouter(hydroserver_publisher, failed_observation)
    worker = threading.Thread(
        target=router.route_incoming_message, name="message_router", daemon=True
    )
    worker.start()
    retry_worker = RetryWorker(
        failed_observation,
        hydroserver_publisher,
        config.retry_interval,
        config.max_retry_attempt,
    )
    retry_worker_thread = threading.Thread(
        target=retry_worker.run, name="retry_worker", daemon=True
    )
    retry_worker_thread.start()
    try:
        mqtt.connect()
    # pylint: disable=broad-exception-caught
    except Exception:
        logger.exception("MQTT service failed.")
    finally:
        mqtt.stop()
        retry_worker.stop()
        retry_worker_thread.join(timeout=10)
        logger.info("All service shutdown")


if __name__ == "__main__":
    main()

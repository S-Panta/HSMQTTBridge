import threading
import logging
from queue import Queue
from settings import settings
from database.retry_buffer import RetryBuffer
from mqtt_consumer import MQTTConsumer
from message_router import MessageRouter
from publisher.hydroserver.publisher import HydroServerPublisher
from publisher.hydroserver.retry_worker import RetryWorker


def setup_logging():
    root = logging.getLogger()

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(threadName)s - %(message)s"
    )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    root.addHandler(handler)
    root.setLevel(getattr(logging, settings.log_level))


def main():
    # setting up logger first
    setup_logging()
    logger = logging.getLogger(__name__)
    task_queue = Queue()

    retry_buffer = RetryBuffer(settings.db_path)
    hydroserver_publisher = HydroServerPublisher(
        settings.hydroserver_url,
        settings.workspace_api_key,
    )

    mqtt = MQTTConsumer(
        host=settings.mqtt_broker_url,
        port=settings.mqtt_broker_port,
        client_id=settings.mqtt_client_id,
        username=settings.mqtt_username,
        password=settings.mqtt_password,
        keepalive=settings.mqtt_keepalive,
        topic_filter=settings.mqtt_topic_filter,
        task_queue=task_queue,
    )

    router = MessageRouter(hydroserver_publisher, retry_buffer, task_queue)
    worker = threading.Thread(
        target=router.route_incoming_message, name="message_router", daemon=True
    )
    retry_worker = RetryWorker(
        retry_buffer,
        hydroserver_publisher,
        settings.retry_interval,
        settings.max_retry_attempt,
    )
    retry_worker_thread = threading.Thread(
        target=retry_worker.run, name="retry_worker", daemon=True
    )

    try:
        worker.start()
        retry_worker_thread.start()
        mqtt.connect()

    except Exception:  # pylint: disable=broad-exception-caught
        logger.exception("MQTT service failed.")
    finally:
        mqtt.stop()
        retry_worker.stop()
        retry_worker_thread.join(timeout=10)
        logger.info("All service shutdown")


if __name__ == "__main__":
    main()

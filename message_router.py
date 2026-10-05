import json
import logging
from paho.mqtt.client import topic_matches_sub
from settings import settings
from queue_manager import taskqueue

logger = logging.getLogger(__name__)


class MessageRouter:
    """A bridge between MQTT Subscriber and other services"""

    def __init__(self, hydroserver_publisher, retry_buffer):
        self.hydroserver_publisher = hydroserver_publisher
        self.retry_buffer = retry_buffer

    def route_incoming_message(self):
        logger.info("Starting message router")

        while True:
            topic, payload = taskqueue.get()

            if topic.endswith("/lwt"):
                # to-do: implement notification service
                logger.info("topic '%s' routed to Notification service", topic)
                continue

            if any(
                topic_matches_sub(route, topic)
                for route in settings.hydroserver_topic_routes
            ):
                logger.info("Topic routed to HydroServer")
                try:
                    data = json.loads(payload)
                except json.JSONDecodeError:
                    logger.error(
                        "Invalid JSON payload received on topic '%s': %s",
                        topic,
                        payload,
                    )
                    continue
                result = self.hydroserver_publisher.push_observation_to_upstream(data)
                if result and result.should_retry is True:
                    logger.warning(
                        "HydroServer publish failed; buffering for retry: topic=%s",
                        topic,
                    )
                    self.retry_buffer.insert(data, topic, result)

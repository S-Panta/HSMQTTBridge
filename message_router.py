import json
import logging
from paho.mqtt.client import topic_matches_sub
from settings import settings

# from queue_manager import taskqueue

logger = logging.getLogger(__name__)


class MessageRouter:
    """A bridge between MQTT Subscriber and other services"""

    def __init__(self, hydroserver_publisher, retry_buffer, task_queue):
        self.hydroserver_publisher = hydroserver_publisher
        self.retry_buffer = retry_buffer
        self.task_queue = task_queue

    def route_incoming_message(self):
        logger.info("Starting message router")

        while True:
            topic, payload = self.task_queue.get()

            if topic.endswith("/lwt"):
                # to-do: implement notification service
                logger.debug("topic '%s' routed to Notification service", topic)
                continue

            if any(
                topic_matches_sub(route, topic)
                for route in settings.hydroserver_topic_routes
            ):
                logger.debug("Topic %s routed to HydroServer", topic)
                try:
                    observation = json.loads(payload)
                except json.JSONDecodeError:
                    logger.error(
                        "Invalid JSON payload received on topic '%s': %s",
                        topic,
                        payload,
                    )
                    continue
                result = self.hydroserver_publisher.post_observation(observation)
                if result is None:
                    logger.info(
                        "Published observation to the hydroserver of topic=%s", topic
                    )
                elif result and result.should_retry is True:
                    logger.debug(
                        "HydroServer publish failed; buffering for retry: topic=%s",
                        topic,
                    )
                    self.retry_buffer.insert(observation, topic, result)
                else:
                    logger.debug(
                        "Observation of topic %s rejected from both hydroserver and retry buffer"
                        "because of %d status code",
                        topic,
                        result.status_code,
                    )

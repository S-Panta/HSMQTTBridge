import json
import logging
from queue_manager import taskqueue

logger = logging.getLogger(__name__)


class MessageRouter:
    """A bridge between MQTT Subscriber and other services"""

    def __init__(self, hydroserver_publisher, pending_observation):
        self.hydroserver_publisher = hydroserver_publisher
        self.pending_observation = pending_observation

    def route_incoming_message(self):
        logger.info("Starting message router")

        while True:
            topic, payload = taskqueue.get()
            # for example: topic ending with /lwt could be directed to notification service
            # every observation topic ends with observation name; this make filtering easy
            # if topic.endswith(("temperature", "pH")):
            if topic.endswith("temperature"):
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
                if result and result.cache_data is True:
                    logger.info("Caching data to sqlite database")
                    self.pending_observation.insert(data, topic, result)

import json
from queue_manager import taskqueue


class MessageRouter:
    """A bridge between MQTT Subscriber and other services"""

    def __init__(self, hydroserver_publisher, pending_observation):
        self.hydroserver_publisher = hydroserver_publisher
        self.pending_observation = pending_observation

    def route_incoming_message(self):
        print("running new threads")
        while True:
            topic, payload = taskqueue.get()
            try:
                data = json.loads(payload)
            except json.JSONDecodeError:
                print(f"Bad payload on {topic}: {payload}")
                continue
            # for example: topic ending with /lwt could be directed to notification service
            # every observation topic ends with observation name; this make filtering easy
            # if topic.endswith(("temperature", "pH")):
            if topic.endswith("temperature"):

                result = self.hydroserver_publisher.push_observation_to_upstream(data)
                if result and result.cache_data is True:

                    self.pending_observation.insert(data, topic, result)

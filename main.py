import os
import json
import threading
from dotenv import load_dotenv
from queue_manager import taskqueue

from database.pending_observation import PendingObservation
from mqtt.consumer import MQTTClient
from publisher.hydroserver.hydroserver_publisher import HydroServerPublisher

# from publisher.hydroserver.retry_worker import RetryWorker

load_dotenv()

HYDROSERVER_URL = os.getenv("HYDROSERVER_URL")
API_KEY = os.getenv("HYDROSERVER_API_KEY")

MQTT_HOST = "localhost"
MQTT_PORT = 1883

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(PROJECT_DIR, "data", "observation.db")

MQTT_TOPIC_FILTER = "uwrl/#"


class MQTTBridge:
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
                # time.sleep(35)
                if result.cache_data is True:

                    self.pending_observation.insert_observation(data, topic, result)


def main():

    pending_observation = PendingObservation(DB_PATH)
    # retry_worker = RetryWorker(pending_observation)
    hydroserver_publisher = HydroServerPublisher(
        HYDROSERVER_URL,
        API_KEY,
    )

    mqtt = MQTTClient(host=MQTT_HOST, port=MQTT_PORT, topic_prefix=MQTT_TOPIC_FILTER)

    bridge = MQTTBridge(hydroserver_publisher, pending_observation)
    worker = threading.Thread(target=bridge.route_incoming_message, daemon=True)
    worker.start()
    try:
        mqtt.connect()
        mqtt.loop_forever()
    except KeyboardInterrupt:
        print("Shutting down...")
        mqtt.stop()


if __name__ == "__main__":
    main()

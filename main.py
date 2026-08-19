import time
import os
import json
from dotenv import load_dotenv

from database.connection import DatabaseConnection
from mqtt.consumer import MQTTClient
from publisher.hydroserver_publisher import HydroServerPublisher

load_dotenv()

HYDROSERVER_URL = os.getenv("HYDROSERVER_URL")
API_KEY = os.getenv("HYDROSERVER_API_KEY")

MQTT_HOST = "raspberrypi1.mypc.usu.edu"
MQTT_PORT = 1883

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(PROJECT_DIR, "data", "observation.db")

MQTT_TOPIC_FILTER = "uwrl/#"


class MQTTBridge:
    """A bridge between MQTT Subscriber and other services"""

    def __init__(self, hydroserver_publisher, database_connection):
        self.hydroserver_publisher = hydroserver_publisher
        self.database = database_connection

    def route_incoming_message_to_upstream(self, topic, payload):
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            print(f"Bad payload on {topic}: {payload}")
            return
        # for example: topic ending with /lwt could be directed to notification service
        # every observation topic ends with observation name which would make this filtering easy
        # if topic.endswith(("temperature", "pH")):
        if topic.endswith("temperature"):
            result = self.hydroserver_publisher.push_observation_to_upstream(data)
            if result.cache_data is True:
                print("going to databaseeeee")
                print(data)
                self.database.insert_pending_observation(data, topic, result)


def main():
    database_connection = DatabaseConnection(DB_PATH)
    hydroserver_publisher = HydroServerPublisher(
        HYDROSERVER_URL,
        API_KEY,
    )

    bridge = MQTTBridge(hydroserver_publisher, database_connection)

    mqtt = MQTTClient(host=MQTT_HOST, port=MQTT_PORT, topic_prefix=MQTT_TOPIC_FILTER)
    mqtt.add_handler(bridge.route_incoming_message_to_upstream)
    mqtt.connect()
    print(f"Connected to MQTT broker at {MQTT_HOST}:{MQTT_PORT}")

    try:
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        print("Shutting down...")
        mqtt.stop()


if __name__ == "__main__":
    main()

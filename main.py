import time
import os
import json
from dotenv import load_dotenv

from database.connection import DatabaseConnection
from mqtt.consumer import MQTTClient
from hydroserver.publisher import HydroServerPublisher

load_dotenv()

HYDROSERVER_URL = os.getenv("HYDROSERVER_URL")
API_KEY = os.getenv("HYDROSERVER_API_KEY")

MQTT_HOST = "raspberrypi1.mypc.usu.edu"
MQTT_PORT = 1883

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(PROJECT_DIR, "data", "observation.db")
SCHEMA_PATH = os.path.join(PROJECT_DIR, "database", "createtable.sql")

MQTT_TOPIC_FILTER = "uwrl/#"


# pylint: disable=too-few-public-methods
class MQTTBridge:
    """A bridge between MQTT Subscriber and other services"""

    def __init__(self, hydroserver_publisher, db=None):
        self.hydroserver_publisher = hydroserver_publisher
        self.db = db

    def route_incoming_message(self, topic, payload):
        try:
            # print(topic)
            # print(payload)
            # print('...................................')
            data = json.loads(payload)
        except json.JSONDecodeError:
            print(f"Bad payload on {topic}: {payload}")
            return
        # for example: topic ending with /lwt could be directed to notification service
        # every observation topic ends with observation name which would make this filtering easy
        if topic.endswith(("temperature", "pH")):
            self.hydroserver_publisher.post_observation_to_hydroserver(data)


def setup_database():
    connection = DatabaseConnection(DB_PATH)
    with open(SCHEMA_PATH, "r", encoding="utf-8") as file:
        sql_script = file.read()
    connection.execute(sql_script)
    connection.commit()
    return connection


def main():
    db = setup_database()

    hydroserver_publisher = HydroServerPublisher(
        HYDROSERVER_URL,
        API_KEY,
    )

    bridge = MQTTBridge(hydroserver_publisher, db=db)

    mqtt = MQTTClient(host=MQTT_HOST, port=MQTT_PORT, topic_prefix=MQTT_TOPIC_FILTER)
    mqtt.add_handler(bridge.route_incoming_message)
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

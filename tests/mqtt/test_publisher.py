# pylint: skip-file
import json
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

MQTT_HOST = "raspberrypi1.mypc.usu.edu"
MQTT_PORT = 1883
MQTT_TOPIC = "uwrl/arduinopublisher/tempsensorid/temperature"

DATASTREAM_ID = "019eae3f-3450-70db-b5d2-a55879b4d681"


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT broker")
    else:
        print(f"MQTT connection failed: {rc}")


def on_disconnect(client, userdata, rc):
    print(f"Disconnected from MQTT broker: {rc}")


client = mqtt.Client()

client.on_connect = on_connect
client.on_disconnect = on_disconnect

print(f"Connecting to {MQTT_HOST}:{MQTT_PORT}...")

try:
    client.connect(MQTT_HOST, MQTT_PORT, 60)
except Exception as e:
    print(f"Connection error: {e}")
    exit(1)

# Start Paho's network loop in the background
client.loop_start()

try:
    while True:
        temperature = 48.8

        payload = {
            "Datastream": {"@iot.id": DATASTREAM_ID},
            "result": temperature,
            "phenomenonTime": datetime.now(timezone.utc)
            .isoformat(timespec="seconds")
            .replace("+00:00", "Z"),
        }

        payload_json = json.dumps(payload)

        print(f"Publishing to {MQTT_TOPIC}")
        print(payload_json)

        result = client.publish(MQTT_TOPIC, payload_json, qos=1)

        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            print("Published successfully\n")
        else:
            print(f"Publish failed: {result.rc}\n")

        time.sleep(15)

except KeyboardInterrupt:
    print("\nStopping publisher...")

finally:
    client.loop_stop()
    client.disconnect()
    print("Disconnected from MQTT broker.")

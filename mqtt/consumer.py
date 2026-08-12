# pylint: disable=unused-argument
import json
import paho.mqtt.client as mqtt


from hydroserver.publisher import HydroServerPublisher


class MQTTClient:
    """Class for MQTT Publish and Subscribe"""

    # to:do: need to remove this in future
    KEEP_ALIVE = 60
    CLIENT_ID = "bridge_script"
    TOPIC = "uwrl/cr350/temperature"

    def __init__(self, host, port):
        self.client = None
        self.host = host
        self.port = port
        self.client = None
        self.publisher = HydroServerPublisher()

    def connect(self):
        try:
            self.client = mqtt.Client(
                mqtt.CallbackAPIVersion.VERSION2, client_id=self.CLIENT_ID
            )
            self.client.on_connect = self.on_connect
            self.client.on_message = self.on_message
            self.client.on_subscribe = self.on_subscribe
            self.client.on_disconnect = self.on_disconnect
            # self.client.username_pw_set()
            print(f"Connecting to {self.host}:{self.port}...")
            self.client.connect(self.host, self.port, self.KEEP_ALIVE)
            self.client.loop_start()

        # pylint: disable-next=broad-exception-caught
        except Exception as e:
            print(f"Connection to MQTT server failed: {e}")

    # callback when client receives CONNACK from broker
    def on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            print("Successfully connected!")
            client.subscribe(self.TOPIC)
        else:
            print(f"Connection failed: {reason_code}")

    # The callback called when a message has been received on a topic
    # that the client subscribes to
    def on_message(self, client, userdata, message):
        # This is where we write what we want to do when message is received
        # raw byte array (bytes object) is received and therefore decoding before sending to object
        print("this is when a message is fired inside on messsage")
        payload = json.loads(message.payload.decode())
        self.publisher.post_observation_to_hydroserver(payload)
        # self.Observation.post_observation_to_hydroserver(payload)
        # Observation(payload)
        # print(message.topic + "" + str(message.payload))

    # The callback called when the broker responds to a subscribe request
    def on_subscribe(self, client, userdata, mid, reason_code, properties):
        print("subscribe on" + str(mid))

    def on_disconnect(self, client, userdata, reason_code):
        print("Disconnected with server" + str(reason_code))

    def stop(self):
        if self.client is not None:
            self.client.loop_stop()
            self.client = None

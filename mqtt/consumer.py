# pylint: disable=unused-argument,too-many-instance-attributes,too-many-arguments,too-many-positional-arguments
import paho.mqtt.client as mqtt
from queue_manager import taskqueue


class MQTTClient:
    """Class for MQTT Publish and Subscribe"""

    KEEP_ALIVE = 10

    def __init__(
        self,
        host,
        topic_prefix,
        username=None,
        password=None,
        port=1883,
        client_id="pythonbridge",
    ):
        self.client = None
        self.host = host
        self.port = port
        self.topic_prefix = topic_prefix
        self.client_id = client_id
        self.username = username
        self.password = password

    def connect(self):
        try:

            self.client = mqtt.Client(
                mqtt.CallbackAPIVersion.VERSION2, client_id=self.client_id
            )
            # all these callbacks runs on same network thread because of loop_start()
            self.client.on_connect = self.on_connect
            self.client.on_message = self.on_message
            self.client.on_subscribe = self.on_subscribe
            self.client.on_disconnect = self.on_disconnect
            if self.username is not None:
                self.client.username_pw_set(self.username, self.password)
            print(f"Connecting to {self.host}:{self.port}")
            self.client.connect(self.host, self.port, self.KEEP_ALIVE)

        # pylint: disable-next=broad-exception-caught
        except Exception as e:
            print(f"Connection to MQTT server failed: {e}")

    # callback when client receives CONNACK from broker
    def on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            print("Successfully connected!")
            client.subscribe(self.topic_prefix)
            # there is no way of knowing how many topic exists in the broker of this prefix
            # it can be known in self.on_message step
            print(f"Subscribed to {self.topic_prefix}")
        else:
            print(f"Connection failed: {reason_code}")

    # The callback called when a message has been received on a topic
    # that the client subscribes to
    def on_message(self, client, userdata, message):
        # This is where we write what we want to do when message is received
        # raw byte array (bytes object) is received and therefore decoding before sending to object
        # print(message.payload.decode())
        taskqueue.put((message.topic, message.payload.decode()))

    # The callback called when the broker responds to a subscribe request
    def on_subscribe(self, client, userdata, mid, reason_code, properties):
        print("subscribe on" + str(mid))

    def on_disconnect(
        self, client, userdata, disconnect_flags, reason_code, properties
    ):
        print(
            f"Disconnected with server: "
            f"reason={reason_code}, "
            f"flags={disconnect_flags}"
        )

    def stop(self):
        if self.client is not None:
            self.client.disconnect()
            self.client.loop_stop()
            self.client = None

    def loop_forever(self):
        self.client.loop_forever()

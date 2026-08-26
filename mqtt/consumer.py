# pylint: disable=unused-argument,too-many-instance-attributes,too-many-arguments,too-many-positional-arguments
import logging
import socket
import paho.mqtt.client as mqtt
from queue_manager import taskqueue

logger = logging.getLogger(__name__)


class MQTTClient:
    """Class for MQTT Publish and Subscribe"""

    KEEP_ALIVE = 60

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
            logger.info(
                "Connecting to MQTT broker %s:%s (client_id=%s)",
                self.host,
                self.port,
                self.client_id,
            )
            self.client.connect(self.host, self.port, self.KEEP_ALIVE)
            self.client.loop_forever()

        except (
            ConnectionRefusedError,
            TimeoutError,
            socket.gaierror,
            OSError,
        ):
            logger.exception(
                "Network connection to MQTT broker %s:%s failed",
                self.host,
                self.port,
            )

    # callback when client receives CONNACK from broker
    def on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            logger.info(
                "Connected to MQTT broker host=%s port=%s client_id=%s",
                self.host,
                self.port,
                self.client_id,
            )
            client.subscribe(self.topic_prefix)
            # there is no way of knowing how many topic exists in the broker of this prefix
            # it can be known in self.on_message step
            logger.info("Subscribed to %s", self.topic_prefix)
        else:
            logger.error(
                "MQTT connection failed: reason_code=%s",
                reason_code,
            )

    # The callback called when a message has been received on a topic
    # that the client subscribes to
    def on_message(self, client, userdata, message):
        logger.debug(
            "Received MQTT message topic=%s qos=%s retained=%s",
            message.topic,
            message.qos,
            message.retain,
        )
        # This is where we write what we want to do when message is received
        # raw byte array (bytes object) is received and therefore decoding before sending to object
        try:
            payload = message.payload.decode()
            taskqueue.put((message.topic, payload))

        except UnicodeDecodeError:
            logger.exception(
                "Failed to decode MQTT message received on topic %s",
                message.topic,
            )

    # The callback called when the broker responds to a subscribe request
    def on_subscribe(self, client, userdata, mid, reason_code, properties):
        logger.info(
            "MQTT SUBACK reason codes: %s",
            reason_code,
        )

    def on_disconnect(
        self, client, userdata, disconnect_flags, reason_code, properties
    ):
        logger.info(
            "Disconnected with server: reason=%s, flags=%s",
            reason_code,
            disconnect_flags,
        )

    def stop(self):
        if self.client is not None:
            self.client.disconnect()
            self.client.loop_stop()
            self.client = None
        logger.info("MQTT client stopped")

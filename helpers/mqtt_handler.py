import paho.mqtt.client as mqtt
import logging
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MqttHandler:
    def __init__(self, broker_url, broker_port, topic, username, password):
        """
        Initialize MqttHandler with broker details, topic, and user credentials.

        Parameters
        ----------
        broker_url : str
            The URL of the MQTT broker.
        broker_port : int
            The port on which the MQTT broker is running.
        topic : str
            The topic to which messages will be published.
        username : str
            The username for MQTT broker authentication.
        password : str
            The password for MQTT broker authentication.
        """
        self.broker_url = broker_url
        self.broker_port = broker_port
        self.topic = topic
        self.username = username
        self.password = password
        self.client = mqtt.Client()
        self.client.username_pw_set(self.username, self.password)

    def connect(self):
        """
        Connect to the MQTT broker.
        """
        try:
            self.client.connect(self.broker_url, self.broker_port)
            logger.info(f"Connected to MQTT broker at {self.broker_url}:{self.broker_port}")
        except Exception as e:
            logger.error(f"Could not connect to MQTT broker: {e}")
            raise

    def publish(self, payload):
        """
        Publish a message to the MQTT broker.

        Parameters
        ----------
        payload : dict
            The data to be published.

        Returns
        -------
        bool
            True if the message was published successfully, False otherwise.
        """
        try:
            result = self.client.publish(self.topic, json.dumps(payload))
            result.wait_for_publish()
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"Message published to topic {self.topic}: {payload}")
                return True
            else:
                logger.error(f"Failed to publish message: {result.rc}")
                return False
        except Exception as e:
            logger.error(f"Error publishing message to MQTT: {e}")
            return False

# Usage
if __name__ == "__main__":
    # Example usage of the MqttHandler
    mqtt_handler = MqttHandler(broker_url="192.168.1.69", broker_port=1883, topic="sensor/data", username="glen", password="password")
    try:
        mqtt_handler.connect()
    
        sample_data = {'temperature': 25, 'humidity': 50}
        success = mqtt_handler.publish(sample_data)
        if success:
            logger.info("Payload published successfully.")
        else:
            logger.error("Failed to publish payload.")
    except Exception as e:
        logger.fatal(f"Failed to initialize and connect to MQTT broker: {e}")
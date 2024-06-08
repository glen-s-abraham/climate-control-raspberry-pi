import os
import time
import logging
import json
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
import csv
import board

from helpers.sensor_reader import SensorReader
from helpers.relay_controller import RelayController
from helpers.mqtt_handler import MqttHandler

# Constants
SLEEP_DURATION_SENSOR = 10  # Sensor data collection interval (10 seconds)
SENSOR_PUBLISH_INTERVAL = 3600  # Interval to publish sensor data to MQTT (60 seconds)
HUMIDITY_THRESHOLD_LOW = 81  # Humidity lower-bound threshold
HUMIDITY_THRESHOLD_HIGH = 89  # Humidity upper-bound threshold
HUMIDITY_ALERT_THRESHOLD = 75  # Extra humidity level threshold for sending notifications
NOTIFY_INTERVAL = timedelta(minutes=30)  # Notification interval for low humidity alerts
RELAY_PINS = {
    'relay1': 17,
    'relay2': 18
}
CSV_HEADER = ['Timestamp', 'Temperature_F', 'Temperature_C', 'Humidity', 'Relay1', 'Relay2']

# MQTT Constants
MQTT_BROKER_URL = "192.168.1.69"
MQTT_BROKER_PORT = 1883
MQTT_USERNAME = "glen"
MQTT_PASSWORD = "password"
MQTT_SENSOR_TOPIC = "sensor/data"
MQTT_RELAY_TOPIC = "relay/status"
MQTT_ERROR_TOPIC = "sensor/error"

# Configure logging
home_directory = os.path.expanduser('~')
LOG_FILE_PATH = os.path.join(home_directory, 'climate_control.log')
CSV_FILE_PATH = os.path.join(home_directory, 'sensor_readings.csv')

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        RotatingFileHandler(LOG_FILE_PATH, maxBytes=10240, backupCount=5)
    ]
)
logger = logging.getLogger(__name__)

# Initialize sensor and relay controller classes
sensor_reader = SensorReader(board.D15)
relay_controller = RelayController(RELAY_PINS)

# Initialize MQTT handler
mqtt_handler = MqttHandler(
    broker_url=MQTT_BROKER_URL,
    broker_port=MQTT_BROKER_PORT,
    topic="",
    username=MQTT_USERNAME,
    password=MQTT_PASSWORD
)
mqtt_handler.connect()

def publish_sensor_data(timestamp, temperature_f, temperature_c, humidity):
    """Publish sensor data to MQTT."""
    payload = {
        'timestamp': timestamp,
        'temperature_f': temperature_f,
        'temperature_c': temperature_c,
        'humidity': humidity
    }
    mqtt_handler.topic = MQTT_SENSOR_TOPIC
    success = mqtt_handler.publish(payload)
    if success:
        logger.info(f"Sensor data published to topic {MQTT_SENSOR_TOPIC}: {payload}")
    else:
        logger.error("Failed to publish sensor data to MQTT")

def publish_relay_status(relay_status, message, timestamp):
    """Publish relay status to MQTT with a triggering event message and timestamp."""
    payload = {
        'timestamp': timestamp,
        'relay1': relay_status['relay1'],
        'relay2': relay_status['relay2'],
        'message': message
    }
    mqtt_handler.topic = MQTT_RELAY_TOPIC
    success = mqtt_handler.publish(payload)
    if success:
        logger.info(f"Relay status published to topic {MQTT_RELAY_TOPIC}: {payload}")
    else:
        logger.error("Failed to publish relay status to MQTT")

def publish_error_message(error_msg):
    """Publish error message to MQTT."""
    payload = {
        'timestamp': datetime.now().astimezone().isoformat(),
        'error': error_msg
    }
    mqtt_handler.topic = MQTT_ERROR_TOPIC
    success = mqtt_handler.publish(payload)
    if success:
        logger.info(f"Error message published to topic {MQTT_ERROR_TOPIC}: {payload}")
    else:
        logger.error("Failed to publish error message to MQTT")

def write_to_csv(timestamp, temperature_f, temperature_c, humidity, relay_status):
    """Write sensor and relay data to a CSV file."""
    with open(CSV_FILE_PATH, 'a', newline='') as file:
        csv_writer = csv.writer(file)
        csv_writer.writerow([timestamp, temperature_f, temperature_c, humidity, relay_status['relay1'], relay_status['relay2']])

def check_conditions_and_toggle_relays(temperature_c, humidity, relay_status, timestamp):
    """Check the conditions and toggle the relays, logging status changes."""
    try:
        if humidity < HUMIDITY_THRESHOLD_LOW and relay_status['relay1'] != 'ON':
            relay_controller.set_relay_state('relay1', 'ON')
            relay_status['relay1'] = 'ON'
            message = f"Humidity below {HUMIDITY_THRESHOLD_LOW}. Relay1 turned ON."
            logger.info("Relay relay1 state changed to ON.")
            publish_relay_status(relay_status, message, timestamp)
        elif humidity >= HUMIDITY_THRESHOLD_HIGH and relay_status['relay1'] != 'OFF':
            relay_controller.set_relay_state('relay1', 'OFF')
            relay_status['relay1'] = 'OFF'
            message = f"Humidity above {HUMIDITY_THRESHOLD_HIGH}. Relay1 turned OFF."
            logger.info("Relay relay1 state changed to OFF.")
            publish_relay_status(relay_status, message, timestamp)
    except Exception as e:
        logger.error(f"An error occurred while toggling relays: {e}")
        publish_error_message(str(e))

def manage_relay2_timing(last_toggle_time, relay_status, timestamp):
    """Manage relay2 to turn on for a specified duration within an interval."""
    try:
        current_time = datetime.now().astimezone()
        interval_duration = timedelta(minutes=60)  # Interval duration (1 hour)
        on_duration = timedelta(minutes=10)       # ON duration (15 minutes)

        if relay_status['relay2'] == 'ON':
            # Turn off if the ON duration has passed
            if current_time - last_toggle_time >= on_duration:
                relay_controller.set_relay_state('relay2', 'OFF')
                relay_status['relay2'] = 'OFF'
                message = "Relay2 turned OFF due to time interval."
                logger.info("Relay relay2 state changed to OFF due to time interval.")
                publish_relay_status(relay_status, message, timestamp)
                last_toggle_time = current_time  # Reset the toggle time when it turns off
        else:
            # Turn on if the OFF duration (interval - on_duration) has passed
            if current_time - last_toggle_time >= interval_duration - on_duration:
                relay_controller.set_relay_state('relay2', 'ON')
                relay_status['relay2'] = 'ON'
                message = "Relay2 turned ON due to time interval."
                logger.info("Relay relay2 state changed to ON due to time interval.")
                publish_relay_status(relay_status, message, timestamp)
                last_toggle_time = current_time  # Reset the toggle time when it turns on
    except Exception as e:
        logger.error(f"An error occurred while managing relay2 timing: {e}")
        publish_error_message(str(e))
    return last_toggle_time

def initialize_relays():
    """Initialize the relays to the OFF state both logically and physically."""
    for relay in RELAY_PINS:
        relay_controller.set_relay_state(relay, 'OFF')

def initialize_csv():
    """Initialize CSV file with header if it does not exist."""
    if not os.path.exists(CSV_FILE_PATH):
        with open(CSV_FILE_PATH, 'w', newline='') as file:
            csv_writer = csv.writer(file)
            csv_writer.writerow(CSV_HEADER)

def main():
    """Main function that runs the sensor monitoring loop."""
    initialize_csv()

    relay_status = {relay: 'OFF' for relay in RELAY_PINS}  # Assume relays start in the OFF state
    initialize_relays()
    last_sensor_reading_time = time.time() - SLEEP_DURATION_SENSOR
    last_sensor_publish_time = time.time() - SENSOR_PUBLISH_INTERVAL
    last_relay2_toggle_time = datetime.now().astimezone()

    while True:
        try:
            current_time = time.time()
            if current_time - last_sensor_reading_time >= SLEEP_DURATION_SENSOR:
                timestamp = datetime.now().astimezone().isoformat()
                temperature_f, temperature_c, humidity = sensor_reader.read_sensor_data()
                last_sensor_reading_time = current_time

                logger.info(f"Sensor data: Temp: {temperature_f:.1f} F / {temperature_c:.1f} C, Humidity: {humidity}%")
                check_conditions_and_toggle_relays(temperature_c, humidity, relay_status, timestamp)
                write_to_csv(timestamp, temperature_f, temperature_c, humidity, relay_status)

                # Publish sensor data to MQTT only after the specified interval
                if current_time - last_sensor_publish_time >= SENSOR_PUBLISH_INTERVAL:
                    publish_sensor_data(timestamp, temperature_f, temperature_c, humidity)
                    last_sensor_publish_time = current_time

                last_relay2_toggle_time = manage_relay2_timing(last_relay2_toggle_time, relay_status, timestamp)  # Manage relay2 timing

        except Exception as e:
            logger.error(f"An exception occurred: {e}")
            publish_error_message(str(e))

        time.sleep(1)  # Sleep at the end of each loop iteration to reduce CPU usage

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Script execution interrupted by user.")
    finally:
        relay_controller.cleanup()
        logger.info("GPIO cleanup completed and program terminated.")
import os
from datetime import datetime
import time
import logging
from logging.handlers import RotatingFileHandler
import csv
import board
from helpers.sensor_reader import SensorReader
from helpers.relay_controller import RelayController
from helpers.mail_helper import send_email

# Constants
SLEEP_DURATION_SENSOR = 10  # Sensor data collection interval (10 seconds)
HUMIDITY_THRESHOLD_LOW = 81  # Humidity lower-bound threshold
HUMIDITY_THRESHOLD_HIGH = 87  # Humidity upper-bound threshold
TEMPERATURE_THRESHOLD_LOW = 28  # Temperature lower-bound threshold
TEMPERATURE_THRESHOLD_HIGH = 30  # Temperature upper-bound threshold
HUMIDITY_ALERT_THRESHOLD = 75  # Extra humidity level threshold for sending notifications
RELAY_PINS = {
    'relay1': 17,
    'relay2': 18
}
MAILING_LIST = ["glenabraham27@gmail.com", "liyasunny2005@gmail.com"]
CSV_HEADER = ['Timestamp', 'Temperature_F', 'Temperature_C', 'Humidity', 'Relay1', 'Relay2']

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

def send_relay_status_email(relay_name, status, humidity):
    """
    Send email notification about the relay's status change.
    
    Parameters
    ----------
    relay_name : str
        The name of the relay.
    status : str
        The new status of the relay (ON or OFF).
    humidity : float
        The current humidity level when the relay status changed.
    """
    subject = f"Humidifier Status: {status}"
    message = f"Humidifier Turned {status.lower()} in fruiting room! Humidity level: {humidity}."
    send_email(subject, message, MAILING_LIST)
    logger.info(f"{relay_name} state changed to {status}.")

def notify_low_humidity_if_relay_on(humidity, relay_status):
    """
    Notify via email if the humidity drops below the alert threshold
    and the humidifier relay is turned on.
    
    Parameters
    ----------
    humidity : float
        Current humidity level.
    relay_status : dict
        Dictionary containing the status of the relays.
    """
    if humidity < HUMIDITY_ALERT_THRESHOLD and relay_status['relay1'] == 'ON':
        subject = "Low Humidity Alert"
        message = f"Humidity level dropped below {HUMIDITY_ALERT_THRESHOLD}% with the humidifier ON."
        send_email(subject, message, MAILING_LIST)
        logger.info("Email sent due to low humidity level with humidifier ON.")

def write_to_csv(timestamp, temperature_f, temperature_c, humidity, relay_status):
    """
    Write sensor and relay data to a CSV file.
    
    Parameters
    ----------
    timestamp : datetime
        The current timestamp.
    temperature_f : float
        Temperature in Fahrenheit.
    temperature_c : float
        Temperature in Celsius.
    humidity : float
        Current humidity level.
    relay_status : dict
        Dictionary containing the status of the relays.
    """
    with open(CSV_FILE_PATH, 'a', newline='') as file:
        csv_writer = csv.writer(file)
        csv_writer.writerow([timestamp, temperature_f, temperature_c, humidity, relay_status['relay1'], relay_status['relay2']])

def check_conditions_and_toggle_relays(temperature_c, humidity, relay_status):
    """
    Check the conditions and toggle the relays, sending emails when necessary.
    
    Parameters
    ----------
    temperature_c : float
        Current temperature in Celsius.
    humidity : float
        Current humidity level.
    relay_status : dict
        Dictionary containing the status of the relays.
    """
    try:
        if humidity < HUMIDITY_THRESHOLD_LOW and relay_status['relay1'] != 'ON':
            relay_controller.set_relay_state('relay1', 'ON')
            relay_status['relay1'] = 'ON'
            logger.info("Relay relay1 state changed to ON.")
            send_relay_status_email('relay1', 'ON', humidity)

        elif humidity >= HUMIDITY_THRESHOLD_HIGH and relay_status['relay1'] != 'OFF':
            relay_controller.set_relay_state('relay1', 'OFF')
            relay_status['relay1'] = 'OFF'
            logger.info("Relay relay1 state changed to OFF.")
            send_relay_status_email('relay1', 'OFF', humidity)

        if temperature_c < TEMPERATURE_THRESHOLD_LOW and relay_status['relay2'] != 'OFF':
            relay_controller.set_relay_state('relay2', 'OFF')
            relay_status['relay2'] = 'OFF'
            logger.info("Relay relay2 state changed to OFF.")

        elif temperature_c >= TEMPERATURE_THRESHOLD_HIGH and relay_status['relay2'] != 'ON':
            relay_controller.set_relay_state('relay2', 'ON')
            relay_status['relay2'] = 'ON'
            logger.info("Relay relay2 state changed to ON.")
    except Exception as e:
        logger.error(f"An error occurred while toggling relays: {e}")

def initialize_csv():
    """
    Initialize CSV file with header if it does not exist.
    """
    if not os.path.exists(CSV_FILE_PATH):
        with open(CSV_FILE_PATH, 'w', newline='') as file:
            csv_writer = csv.writer(file)
            csv_writer.writerow(CSV_HEADER)

def main():
    """
    Main function that runs the sensor monitoring loop.
    """
    initialize_csv()

    relay_status = {relay: 'OFF' for relay in RELAY_PINS}  # Assume relays start in the OFF state
    last_sensor_reading_time = time.time() - SLEEP_DURATION_SENSOR

    while True:
        try:
            current_time = time.time()
            if current_time - last_sensor_reading_time >= SLEEP_DURATION_SENSOR:
                timestamp = datetime.now().isoformat()
                temperature_f, temperature_c, humidity = sensor_reader.read_sensor_data()
                last_sensor_reading_time = current_time

                logger.info(f"Sensor data: Temp: {temperature_f:.1f} F / {temperature_c:.1f} C, Humidity: {humidity}%")
                check_conditions_and_toggle_relays(temperature_c, humidity, relay_status)
                notify_low_humidity_if_relay_on(humidity, relay_status)  # Check for low humidity and notify if necessary
                write_to_csv(timestamp, temperature_f, temperature_c, humidity, relay_status)

        except Exception as e:
            logger.error(f"An exception occurred: {e}")

        time.sleep(1)  # Sleep at the end of each loop iteration to reduce CPU usage

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Script execution interrupted by user.")
    finally:
        relay_controller.cleanup()
        logger.info("GPIO cleanup completed and program terminated.")
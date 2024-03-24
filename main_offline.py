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
SLEEP_DURATION_SENSOR = 10    # Sensor data collection interval (10 seconds)
HUMIDITY_THRESHOLD_LOW = 81   # Humidity lower-bound threshold
HUMIDITY_THRESHOLD_HIGH = 87  # Humidity upper-bound threshold
TEMPERATURE_THRESHOLD_LOW = 28  # Temperature lower-bound threshold
TEMPERATURE_THRESHOLD_HIGH = 30  # Temperature upper-bound threshold
RELAY_PINS = {
    'relay1': 17,
    'relay2': 18
}

MAILING_LIST = ["glenabraham27@gmail.com","liyasunny2005@gmail.com"]

# Setup logging
home_directory = os.path.expanduser('~')
log_file_path = os.path.join(home_directory, 'climate_control.log')


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler()
logger.addHandler(console_handler)

CSV_FILE_PATH = os.path.join(home_directory, 'sensor_readings.csv') 

# Introduce a RotatingFileHandler to limit log file sizes
file_handler = RotatingFileHandler(log_file_path, maxBytes=10240, backupCount=5)
logger.addHandler(file_handler)

# Initialize sensor and relay controller classes
sensor_reader = SensorReader(board.D15)
relay_controller = RelayController(RELAY_PINS)


def write_to_csv(temperature_f, temperature_c, humidity, relay_status):
    """Writes sensor and relay data to a CSV file."""
    with open(CSV_FILE_PATH, 'a', newline='') as file:
        timestamp = datetime.now().isoformat()
        csv_writer = csv.writer(file)
        csv_writer.writerow([timestamp, temperature_f, temperature_c, humidity, relay_status['relay1'], relay_status['relay2']])


def check_conditions_and_toggle_relays(temperature_c, humidity, relay_status):
    """Check the conditions and toggle the relays accordingly."""
    try:
        if humidity < HUMIDITY_THRESHOLD_LOW and relay_status['relay1'] != 'ON':
            relay_controller.set_relay_state('relay1', 'ON')
            relay_status['relay1'] = 'ON'
            send_email("Humidifier Status",f"Humidifier Turned on in fruiting room! Hulidity level {humidity}.",MAILING_LIST)
            logger.info("Relay relay1 state changed to ON.")

        elif humidity >= HUMIDITY_THRESHOLD_HIGH and relay_status['relay1'] != 'OFF':
            relay_controller.set_relay_state('relay1', 'OFF')
            relay_status['relay1'] = 'OFF'
            send_email("Humidifier Status",f"Humidifier Turned off in fruiting room! Hulidity level {humidity}",MAILING_LIST)
            logger.info("Relay relay1 state changed to OFF.")

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


def main():
    """Main function that runs the sensor monitoring loop."""
    last_sensor_reading_time = time.time() - SLEEP_DURATION_SENSOR  # Force immediate first read
    relay_status = {relay: None for relay in RELAY_PINS}  # Initialize relay statuses to None

    # Initialize CSV file with header
    # Initialize CSV file with header if it does not exist
    if not os.path.exists(CSV_FILE_PATH):
        with open(CSV_FILE_PATH, 'w', newline='') as file:
            csv_writer = csv.writer(file)
            csv_writer.writerow(['Timestamp', 'Temperature_F', 'Temperature_C', 'Humidity', 'Relay1', 'Relay2'])
    while True:
        try:
            current_time = time.time()
            
            # Get sensor readings periodically
            if current_time - last_sensor_reading_time >= SLEEP_DURATION_SENSOR:
                temperature_f, temperature_c, humidity = sensor_reader.read_sensor_data()
                last_sensor_reading_time = current_time
                logger.info(f"Sensor data: Temp: {temperature_f:.1f} F / {temperature_c:.1f} C, Humidity: {humidity}%")
                
                # Check conditions and set relay states
                check_conditions_and_toggle_relays(temperature_c, humidity, relay_status)
                
                # Write to CSV
                write_to_csv(temperature_f, temperature_c, humidity, relay_status)
        except Exception as e:
            logger.error(f"An exception occurred: {e}")

        # Sleep between iterations to reduce CPU usage
        time.sleep(1)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Script execution interrupted by user.")
    finally:
        relay_controller.cleanup()
        logger.info("GPIO cleanup completed and program terminated.")

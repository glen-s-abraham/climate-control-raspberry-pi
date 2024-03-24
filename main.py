import os
import time
import threading
import logging
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for
from logging.handlers import RotatingFileHandler
from helpers.sensor_reader import SensorReader
from helpers.relay_controller import RelayController
from helpers.mongo_handler import MongoHandler
import board
import RPi.GPIO as GPIO
from dotenv import find_dotenv,load_dotenv
load_dotenv(find_dotenv())

# Logging configuration for console only
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Console logging only, no file logging
    ]
)

# Constants
SLEEP_DURATION_SENSOR = 10    # sensor data collection interval in seconds
SLEEP_DURATION_DB = 300       # database update interval in seconds
HUMIDITY_THRESHOLD_LOW = 80   # Humidity lower-bound threshold
HUMIDITY_THRESHOLD_HIGH = 90  # Humidity upper-bound threshold
TEMPERATURE_THRESHOLD_LOW = 28 # Temperature lower-bound threshold
TEMPERATURE_THRESHOLD_HIGH = 30 # Temperature upper-bound threshold

# MongoDB configuration
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017/")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "sensor_data")
MONGO_COLLECTION_NAME = os.getenv("MONGO_COLLECTION_NAME", "readings")

# Relay pins configuration
RELAY_PINS = {'relay1': 17, 'relay2': 18}
relay_status = {'relay1': None, 'relay2': None}

# Initialization of sensor, relay, and MongoDB handler classes
sensor_reader = SensorReader(board.D15)
relay_controller = RelayController(RELAY_PINS)
mongo_handler = MongoHandler(MONGO_URL, MONGO_DB_NAME, MONGO_COLLECTION_NAME)

# Flask app initialization
app = Flask(__name__)

# Global variable to store the latest sensor data
latest_sensor_data = {'temperature_c': None, 'humidity': None}

# Function to log the relay state to MongoDB
def log_relay_state(relay_name, new_state):
    if relay_status[relay_name] != new_state:
        relay_status[relay_name] = new_state
        relay_state_data = {
            "timestamp": datetime.now(),
            "relay_name": relay_name,
            "state": new_state
        }
        success = mongo_handler.insert_data(relay_state_data)
        if success:
            logging.info(f"Relay {relay_name} state changed to {new_state} and logged to MongoDB.")
        else:
            logging.error(f"Failed to log {relay_name} state change to {new_state}.")

# Function to check sensor thresholds and toggle relays
def check_conditions_and_toggle_relays(temperature_c, humidity):
    try:
        if humidity < HUMIDITY_THRESHOLD_LOW and relay_status['relay1'] != 'ON':
            relay_controller.set_relay_state('relay1', 'ON')
            log_relay_state('relay1', 'ON')

        elif humidity >= HUMIDITY_THRESHOLD_HIGH and relay_status['relay1'] != 'OFF':
            relay_controller.set_relay_state('relay1', 'OFF')
            log_relay_state('relay1', 'OFF')

        if temperature_c < TEMPERATURE_THRESHOLD_LOW and relay_status['relay2'] != 'OFF':
            relay_controller.set_relay_state('relay2', 'OFF')
            log_relay_state('relay2', 'OFF')

        elif temperature_c >= TEMPERATURE_THRESHOLD_HIGH and relay_status['relay2'] != 'ON':
            relay_controller.set_relay_state('relay2', 'ON')
            log_relay_state('relay2', 'ON')
    except Exception as e:
        logging.error(f"An error occurred while toggling relays: {e}")

# Web interface routes
@app.route('/toggle_relay', methods=['POST'])
def toggle_relay():
    relay_name = request.form['relay_name']
    new_state = request.form['new_state']
    relay_controller.set_relay_state(relay_name, new_state)
    log_relay_state(relay_name, new_state)
    return redirect(url_for('index'))

@app.route('/')
def index():
    return render_template('index.html', sensor_data=latest_sensor_data, relay_status=relay_status)

# Background loop for climate control
def climate_control_loop():
    last_sensor_reading_time = time.time() - SLEEP_DURATION_SENSOR
    last_db_update_time = time.time() - SLEEP_DURATION_DB

    while True:
        try:
            current_time = time.time()

            if current_time - last_sensor_reading_time >= SLEEP_DURATION_SENSOR:
                temperature_f, temperature_c, humidity = sensor_reader.read_sensor_data()
                last_sensor_reading_time = current_time

                latest_sensor_data['temperature_c'] = temperature_c
                latest_sensor_data['humidity'] = humidity

                logging.info(f"Sensor data: Temp: {temperature_f:.1f} F / {temperature_c:.1f} C, Humidity: {humidity}%")

                if current_time - last_db_update_time >= SLEEP_DURATION_DB:
                    sensor_data = {
                        "timestamp": datetime.now(),
                        "temperature_f": temperature_f,
                        "temperature_c": temperature_c,
                        "humidity": humidity
                    }

                    mongo_handler.insert_data(sensor_data)
                    last_db_update_time = current_time
                    logging.info("Sensor data inserted to MongoDB.")

                check_conditions_and_toggle_relays(temperature_c, humidity)

        except Exception as e:
            logging.error(f"An error occurred: {e}")

        time.sleep(1)

# Entry point to start the web server and the background loop
if __name__ == '__main__':
    # Create a thread for the background loop
    thread = threading.Thread(target=climate_control_loop)
    thread.daemon = True  # Allows the thread to be interrupted and stopped with the main program
    thread.start()
    logging.info("Background thread started.")

    try:
        logging.info("Starting Flask web server.")
        app.run(host='0.0.0.0', port=5000, debug=False)
    except Exception as e:
        logging.error(f"An error occurred: {e}")
    except KeyboardInterrupt:
        logging.info('Web server shutdown')
    finally:
        GPIO.cleanup()
        logging.info("GPIO cleanup completed and program terminated.")

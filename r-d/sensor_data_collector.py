import time
import csv
import board
import adafruit_dht
from datetime import datetime
import logging
import os

# Configure logging
logging.basicConfig(level=logging.ERROR)

# Constants
SLEEP_DURATION = 2.0
CSV_FILE_NAME = 'sensor_data.csv'

def read_sensor_data(dht_device):
    """
    Reads the temperature and humidity from a DHT device.
    
    Parameters
    ----------
    dht_device : adafruit_dht.DHT
        The DHT device from which to read.

    Returns
    -------
    tuple
        The temperature in Fahrenheit and Celsius and the humidity percentage.

    Raises
    ------
    RuntimeError
        If the read from the DHT sensor fails.
    """
    temperature_c = dht_device.temperature
    temperature_f = temperature_c * (9 / 5) + 32
    humidity = dht_device.humidity
    return temperature_f, temperature_c, humidity

def append_to_csv(data, file_name):
    """
    Appends sensor data with a timestamp to a CSV file. Creates the file if it does not exist.

    Parameters
    ----------
    data : list
        The temperature and humidity data to be written, along with the timestamp.
    file_name : str
        The path to the CSV file where data will be appended.
    """
    file_exists = os.path.exists(file_name)
    with open(file_name, mode='a', newline='') as file:
        csv_writer = csv.writer(file)
        # Write headers if the file is being created
        if not file_exists:
            csv_writer.writerow(['Timestamp', 'Temp_F', 'Temp_C', 'Humidity'])
        csv_writer.writerow(data)

def main():
    # Initialize the DHT device
    dht_device = adafruit_dht.DHT22(board.D15)

    while True:
        try:
            # Read data from the sensor
            temperature_f, temperature_c, humidity = read_sensor_data(dht_device)
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            data = [timestamp, temperature_f, temperature_c, humidity]
            append_to_csv(data, CSV_FILE_NAME)
            print(f"Data written to {CSV_FILE_NAME}: Temp: {temperature_f:.1f} F / {temperature_c:.1f} C, Humidity: {humidity}%")

        except RuntimeError as error:
            logging.error(f"Reading from DHT22 failed: {error}")
            time.sleep(SLEEP_DURATION)

        except Exception as error:
            logging.critical(f"An unexpected error occurred: {error}", exc_info=True)

        time.sleep(SLEEP_DURATION)

if __name__ == '__main__':
    main()

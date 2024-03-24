import os
import time
import board
import adafruit_dht
from datetime import datetime
import logging
from pymongo import MongoClient
from urllib.parse import quote_plus

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Constants
SLEEP_DURATION = 300
MONGO_URL = ""

# It's assumed that you have environment variables for MongoDB credentials
MONGO_USER = None #os.environ.get("MONGO_USER")
MONGO_PASSWORD = None #os.environ.get("MONGO_PASSWORD")
MONGO_DB_NAME = "sensor_data"
MONGO_COLLECTION_NAME = "readings"

# Configure the DHT Sensor
DHT_SENSOR_TYPE = adafruit_dht.DHT22
DHT_PIN = board.D15

def create_mongo_client(url, user=None, password=None):
    """
    Create a MongoDB client.
    
    Parameters
    ----------
    url : str
        The MongoDB URL.
    user : str
        The MongoDB username.
    password : str
        The MongoDB password.

    Returns
    -------
    MongoClient
        The MongoDB client object.
    """
    return MongoClient(url)

def read_sensor_data(dht_device):
    # Docstring omitted for brevity
    temperature_c = dht_device.temperature
    temperature_f = temperature_c * (9 / 5) + 32
    humidity = dht_device.humidity
    return temperature_f, temperature_c, humidity

def insert_to_mongodb(client, db_name, collection_name, data):
    """
    Inserts sensor data with a timestamp into MongoDB collection.
    
    Parameters
    ----------
    client : MongoClient
        The MongoDB client object.
    db_name : str
        The name of the MongoDB database.
    collection_name : str
        The name of the MongoDB collection.
    data : dict
        The temperature and humidity data to be inserted along with the timestamp.
    """
    db = client[db_name]
    collection = db[collection_name]
    collection.insert_one(data)

def main():
    try:	
    	# Initialize the MongoDB client
    	mongo_client = create_mongo_client(MONGO_URL)
    	print("created mongo client")
    	# Initialize the DHT device
    	dht_device = adafruit_dht.DHT22(board.D15)
    	print(dht_device)
    except Exception as e:
        print(e)
    while True:
        try:
            temperature_f, temperature_c, humidity = read_sensor_data(dht_device)
            timestamp = datetime.now()
            data = {
                "timestamp": timestamp,
                "temperature_f": temperature_f,
                "temperature_c": temperature_c,
                "humidity": humidity
            }
            insert_to_mongodb(mongo_client, MONGO_DB_NAME, MONGO_COLLECTION_NAME, data)
            logging.info(f"Data inserted to MongoDB: Temp: {temperature_f:.1f} F / {temperature_c:.1f} C, Humidity: {humidity}%")

        except RuntimeError as error:
            logging.error(f"Reading from DHT22 failed: {error}")
            time.sleep(SLEEP_DURATION)

        except Exception as error:
            logging.critical(f"An unexpected error occurred: {error}", exc_info=True)
        
        time.sleep(SLEEP_DURATION)

if __name__ == '__main__':
    main()

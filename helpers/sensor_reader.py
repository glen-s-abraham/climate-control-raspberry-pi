import adafruit_dht
import board
import logging
import RPi.GPIO as GPIO
from helpers.mail_helper import send_email

# Configure logging per best practices (date format included as per the PEP 8)
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)

# Constants should be self-explanatory; note that I've added one for emails
DHT_SENSOR_TYPE = adafruit_dht.DHT22
DHT_PIN = board.D15
MAX_RETRIES = 3
HUMIDITY_BUFFER = 6
TEMPERATURE_BUFFER = -2
RECIPIENTS = ["glenabraham27@gmail.com", "liyasunny2005@gmail.com"]
FAILED_SUBJECT = "Sensor failed!"
FAILED_MESSAGE = "DHT22 Sensor in fruiting room failed!"
SUCCESS_SUBJECT = "Sensor is working"
SUCCESS_MESSAGE = "DHT22 Sensor in fruiting room is now working after previous failure."

class SensorReader:
    def __init__(self, pin, max_retries=MAX_RETRIES):
        """
        Initialize the SensorReader class.

        Parameters
        ----------
        pin : board.Pin
            GPIO pin for the DHT sensor.
        max_retries : int
            Maximum number of retries to attempt when reading the sensor, default is defined by MAX_RETRIES constant.
        """
        self.pin = pin
        self.dht_device = DHT_SENSOR_TYPE(pin)
        self.max_retries = max_retries
        self.sensor_failed_previously = False  # New flag to track previous sensor states

    def read_sensor_data(self):
        """
        Reads the sensor data from the DHT device, retries on error, and sends email notifications on sensor state changes.

        Returns
        -------
        tuple[float, float, float]
            Temperature in Fahrenheit, temperature in Celsius, and humidity percentages.

        Raises
        ------
        RuntimeError
            If unable to read from the sensor after the specified number of retries.
        """
        for attempt in range(self.max_retries):
            try:
                data = self._attempt_read()
                if self.sensor_failed_previously:  # Sending an email on sensor recovery
                    send_email(SUCCESS_SUBJECT, SUCCESS_MESSAGE, RECIPIENTS)
                    self.sensor_failed_previously = False
                return data
            except RuntimeError as e:
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt == self.max_retries - 1:
                    if not self.sensor_failed_previously:
                        send_email(FAILED_SUBJECT, FAILED_MESSAGE, RECIPIENTS)
                        self.sensor_failed_previously = True
                    logger.error("Max retries reached. Unable to read sensor data.")
                    raise
                self._reset_sensor()

    def _attempt_read(self):
        """
        Attempts to read sensor data once.

        Returns
        -------
        tuple[float, float, float]
            Temperature in Fahrenheit, temperature in Celsius, and humidity percentages.

        Raises
        ------
        RuntimeError
            If unable to read from the sensor.
        """
        temperature_c = self.dht_device.temperature
        temperature_f = temperature_c * 9 / 5 + 32
        humidity = self.dht_device.humidity
        
        # Using all(...) to avoid None in the sensor values
        if all(value is not None for value in [temperature_c, humidity]):
            return temperature_f, temperature_c + TEMPERATURE_BUFFER, humidity + HUMIDITY_BUFFER
        else:
            raise RuntimeError("Sensor returned None value.")

    def _reset_sensor(self):
        """
        Resets the DHT device by reinitializing it.
        """
        self.dht_device.exit()
        self.dht_device = DHT_SENSOR_TYPE(self.pin)

# Additional code related to usage of SensorReader would go here

import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)

# Relay 1
GPIO.setup(17, GPIO.OUT)
# Relay 2
GPIO.setup(18, GPIO.OUT)

try:
    while True:
        GPIO.output(17, GPIO.HIGH)
        print('Relay 1 ON')
        time.sleep(60)
        GPIO.output(17, GPIO.LOW)
        time.sleep(60)
        print('Relay 1 OFF')
finally:
    GPIO.cleanup()
